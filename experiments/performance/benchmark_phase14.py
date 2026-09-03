"""Benchmark the Phase 14 scientific-computing hot paths."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import resource
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("configs") / "phase14_v1.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "phase14_v1"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _peak_rss_bytes() -> int:
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return peak if sys.platform == "darwin" else peak * 1024


def _measure(
    workload: Callable[[], dict[str, Any]],
    repetitions: int,
) -> dict[str, Any]:
    durations: list[float] = []
    signatures: list[str] = []
    scientific_result: dict[str, Any] | None = None
    for _ in range(repetitions):
        gc.collect()
        started = perf_counter()
        result = workload()
        durations.append(perf_counter() - started)
        signatures.append(_canonical_digest(result))
        if scientific_result is None:
            scientific_result = result
    assert scientific_result is not None
    return {
        "repetitions": repetitions,
        "seconds": durations,
        "mean_seconds": statistics.mean(durations),
        "stdev_seconds": statistics.stdev(durations) if repetitions > 1 else 0.0,
        "median_seconds": statistics.median(durations),
        "minimum_seconds": min(durations),
        "maximum_seconds": max(durations),
        "peak_rss_bytes": _peak_rss_bytes(),
        "repeat_results_identical": len(set(signatures)) == 1,
        "scientific_result": scientific_result,
    }


def _hardware_workload(specification: dict[str, Any]) -> dict[str, Any]:
    from experiments.li2026.optimize_hardware_resources import (
        _load_json as load_hardware_json,
        _scenario,
        _search_space,
    )
    from experiments.li2026.reproduce_table3_50km import parameters_from_config
    from quantum_telepathy.optimization.hardware import search_hardware_designs

    config_path = (DEFAULT_CONFIG.parent / specification["config_file"]).resolve()
    config = load_hardware_json(config_path)
    baseline_path = (
        config_path.parent / config["baseline"]["table3_config_file"]
    ).resolve()
    baseline = parameters_from_config(load_hardware_json(baseline_path))
    search_space = _search_space(config["search_space"])
    results = []
    for scenario_specification in config["scenarios"]:
        scenario = _scenario(scenario_specification)
        for distance in scenario_specification["distances_km"]:
            results.append(
                search_hardware_designs(
                    baseline=baseline,
                    scenario=scenario,
                    distance_km=float(distance),
                    search_space=search_space,
                )
            )

    signature_values = [
        (
            result.scenario_id,
            result.distance_km,
            result.candidate_count,
            result.evaluated_count,
            result.feasible_count,
            result.pareto_count,
            result.search_status.value,
            None
            if result.recommended is None
            else (
                result.recommended.design,
                result.recommended.n_req,
                result.recommended.r_req,
                result.recommended.r_heg,
                result.recommended.epsilon,
                result.recommended.weighted_cost,
            ),
        )
        for result in results
    ]
    cases = [
        {
            "scenario_id": result.scenario_id,
            "distance_km": result.distance_km,
            "status": result.search_status.value,
            "candidate_count": result.candidate_count,
            "evaluated_count": result.evaluated_count,
            "feasible_count": result.feasible_count,
            "pareto_count": result.pareto_count,
            "recommended_n_req": (
                result.recommended.n_req if result.recommended else None
            ),
        }
        for result in results
    ]
    return {
        "case_count": len(results),
        "candidate_count": sum(result.candidate_count for result in results),
        "scientific_signature_sha256": hashlib.sha256(
            repr(signature_values).encode()
        ).hexdigest(),
        "cases": cases,
    }


def _statistics_workload(specification: dict[str, Any]) -> dict[str, Any]:
    from quantum_telepathy.li2026.statistics import (
        certification_p_value,
        required_score_trials,
        required_trials,
        score_certification_p_value,
    )

    results = []
    for case in specification["cases"]:
        if case["method"] == "exact_binomial":
            n_req = required_trials(
                case["classical_value"], case["quantum_value"], case["alpha"]
            )
            p_value = certification_p_value(
                n_req, case["classical_value"], case["quantum_value"]
            )
            previous_p_value = certification_p_value(
                n_req - 1, case["classical_value"], case["quantum_value"]
            )
        elif case["method"] == "general_score_bound":
            n_req = required_score_trials(
                case["classical_value"],
                case["quantum_value"],
                case["alpha"],
                case["score_min"],
                case["score_max"],
            )
            p_value = score_certification_p_value(
                n_req,
                case["classical_value"],
                case["quantum_value"],
                case["score_min"],
                case["score_max"],
            )
            previous_p_value = score_certification_p_value(
                n_req - 1,
                case["classical_value"],
                case["quantum_value"],
                case["score_min"],
                case["score_max"],
            )
        else:
            raise ValueError(f"unsupported statistics method: {case['method']}")
        results.append(
            {
                "id": case["id"],
                "method": case["method"],
                "n_req": n_req,
                "expected_n_req": case["expected_n_req"],
                "p_value_at_n_req": p_value,
                "p_value_at_previous_round": previous_p_value,
                "alpha": case["alpha"],
            }
        )
    return {"cases": results}


def _figure5_sdp_workload(specification: dict[str, Any]) -> dict[str, Any]:
    from quantum_telepathy.core.xor_game import independent_bernoulli_distribution
    from quantum_telepathy.ding_jiang.fig3 import independent_classical_value
    from quantum_telepathy.ding_jiang.hft import hedging_utility
    from quantum_telepathy.ding_jiang.loss_sdp import find_npa_threshold_lower_bound

    p = float(specification["p"])
    beta = float(specification["beta"])
    distribution = independent_bernoulli_distribution(p)
    utility = hedging_utility(beta)
    classical_value, _ = independent_classical_value(p, beta)
    result = find_npa_threshold_lower_bound(
        distribution,
        utility,
        classical_value,
        efficiency_tolerance=float(specification["efficiency_tolerance"]),
    )
    statuses = sorted(
        {
            status
            for evaluation in result.evaluations
            for status in evaluation.solver_statuses
        }
    )
    return {
        "p": p,
        "beta": beta,
        "classical_value": classical_value,
        "threshold_lower_bound": result.threshold_lower_bound,
        "transition_upper_bound": result.transition_upper_bound,
        "bracket_width": (
            result.transition_upper_bound - result.threshold_lower_bound
        ),
        "evaluation_count": len(result.evaluations),
        "solver_statuses": statuses,
    }


def _run_worker(target: str, config: dict[str, Any]) -> dict[str, Any]:
    specification = config["targets"][target]
    repetitions = int(specification["repetitions"])
    workloads: dict[str, Callable[[], dict[str, Any]]] = {
        "hardware_grid": lambda: _hardware_workload(specification),
        "finite_statistics": lambda: _statistics_workload(specification),
        "figure5_sdp": lambda: _figure5_sdp_workload(specification),
    }
    return _measure(workloads[target], repetitions)


def _worker_process(target: str, config_path: Path) -> dict[str, Any]:
    environment = os.environ.copy()
    local_paths = (str(ROOT), str(ROOT / "src"))
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        os.pathsep.join(local_paths)
        if not existing
        else os.pathsep.join((*local_paths, existing))
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--config",
            str(config_path),
            "--worker",
            target,
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"benchmark worker {target!r} failed:\n{completed.stderr.strip()}"
        )
    return json.loads(completed.stdout)


def _environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "numpy": version("numpy"),
        "scipy": version("scipy"),
        "cvxpy": version("cvxpy"),
    }


def _validate(
    config: dict[str, Any],
    targets: dict[str, dict[str, Any]],
    environment: dict[str, str],
) -> dict[str, dict[str, Any]]:
    hardware_specification = config["targets"]["hardware_grid"]
    hardware = targets["hardware_grid"]
    hardware_result = hardware["scientific_result"]
    baseline = config["historical_baseline"]
    baseline_hardware = baseline["hardware_grid"]
    comparable = (
        environment["python"].split(".")[:2]
        == baseline["environment"]["python"].split(".")[:2]
        and environment["system"] == baseline["environment"]["system"]
        and environment["machine"] == baseline["environment"]["machine"]
    )
    runtime_ratio = (
        hardware["median_seconds"] / baseline_hardware["median_seconds"]
    )

    statistics_cases = targets["finite_statistics"]["scientific_result"]["cases"]
    statistics_pass = all(
        case["n_req"] == case["expected_n_req"]
        and case["p_value_at_n_req"] < case["alpha"]
        and case["p_value_at_previous_round"] >= case["alpha"]
        for case in statistics_cases
    )
    sdp_specification = config["targets"]["figure5_sdp"]
    sdp = targets["figure5_sdp"]["scientific_result"]
    paper_efficiency = float(sdp_specification["paper_representative_efficiency"])
    sdp_pass = (
        sdp["threshold_lower_bound"] <= paper_efficiency
        and paper_efficiency - sdp["threshold_lower_bound"]
        <= float(sdp_specification["maximum_paper_bracket_distance"])
        and sdp["bracket_width"]
        <= float(sdp_specification["maximum_numerical_bracket_width"])
        and set(sdp["solver_statuses"]) <= {"optimal", "optimal_inaccurate"}
    )
    return {
        "hardware_scientific_signature": {
            "status": "PASS"
            if hardware_result["scientific_signature_sha256"]
            == hardware_specification["expected_scientific_signature_sha256"]
            else "FAIL",
            "actual": hardware_result["scientific_signature_sha256"],
            "expected": hardware_specification[
                "expected_scientific_signature_sha256"
            ],
        },
        "hardware_candidate_count": {
            "status": "PASS"
            if hardware_result["candidate_count"]
            == hardware_specification["expected_candidate_count"]
            else "FAIL",
            "actual": hardware_result["candidate_count"],
            "expected": hardware_specification["expected_candidate_count"],
        },
        "hardware_runtime": {
            "status": (
                "PASS"
                if comparable
                and runtime_ratio
                <= hardware_specification["maximum_median_runtime_ratio"]
                else "FAIL" if comparable else "NOT_COMPARABLE"
            ),
            "comparable_environment": comparable,
            "baseline_median_seconds": baseline_hardware["median_seconds"],
            "actual_median_seconds": hardware["median_seconds"],
            "runtime_ratio": runtime_ratio,
            "maximum_ratio": hardware_specification[
                "maximum_median_runtime_ratio"
            ],
        },
        "repeat_determinism": {
            "status": "PASS"
            if all(
                target["repeat_results_identical"] for target in targets.values()
            )
            else "FAIL",
        },
        "finite_statistics": {
            "status": "PASS" if statistics_pass else "FAIL",
            "case_count": len(statistics_cases),
        },
        "figure5_sdp": {
            "status": "PASS" if sdp_pass else "FAIL",
            "paper_representative_efficiency": paper_efficiency,
        },
    }


def benchmark(config_path: Path, output_directory: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    environment = _environment()
    targets = {
        target: _worker_process(target, config_path)
        for target in ("finite_statistics", "figure5_sdp", "hardware_grid")
    }
    validations = _validate(config, targets, environment)
    required_statuses = {
        validation["status"] for validation in validations.values()
    }
    overall_status = "PASS" if required_statuses <= {"PASS"} else "FAIL"
    summary = {
        "schema_version": 1,
        "phase": config["phase"],
        "benchmark_id": config["benchmark_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": environment,
        "historical_baseline": config["historical_baseline"],
        "targets": targets,
        "validations": validations,
        "overall_status": overall_status,
        "notes": config["notes"],
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "phase14_benchmark_summary.json"
    with output_path.open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--worker",
        choices=("hardware_grid", "finite_statistics", "figure5_sdp"),
    )
    arguments = parser.parse_args()
    config_path = arguments.config.resolve()
    if arguments.worker:
        print(json.dumps(_run_worker(arguments.worker, _load_json(config_path))))
        return
    summary = benchmark(config_path, arguments.output.resolve())
    hardware = summary["validations"]["hardware_runtime"]
    print(f"Overall status: {summary['overall_status']}")
    print(f"Hardware-grid median: {hardware['actual_median_seconds']:.3f} s")
    print(f"Historical runtime ratio: {hardware['runtime_ratio']:.3f}")


if __name__ == "__main__":
    main()
