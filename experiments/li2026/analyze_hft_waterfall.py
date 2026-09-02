"""Generate the Phase 11 Ding-to-Li HFT operational-advantage waterfall."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from quantum_telepathy.li2026.hft_waterfall import evaluate_hft_waterfall
from quantum_telepathy.li2026.lctc import enumerated_classical_optimum


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "experiments/li2026/configs/hft_waterfall_v1.json"
DEFAULT_OUTPUT = ROOT / "experiments/li2026/results/hft_waterfall_v1"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _nested(data: dict[str, Any], path: list[str]) -> Any:
    value: Any = data
    for key in path:
        value = value[key]
    return value


def _distribution(
    raw: list[list[float]],
) -> tuple[tuple[float, float], tuple[float, float]]:
    if len(raw) != 2 or any(len(row) != 2 for row in raw):
        raise ValueError("input_distribution must be a 2x2 array")
    return tuple(  # type: ignore[return-value]
        tuple(float(value) for value in row) for row in raw
    )


def _metric(actual: float, expected: float, tolerance: float) -> dict[str, Any]:
    error = abs(actual - expected)
    return {
        "actual": actual,
        "expected": expected,
        "absolute_error": error,
        "tolerance": tolerance,
        "status": "PASS" if error <= tolerance else "FAIL",
    }


def _render_plot(path: Path, results: list[dict[str, Any]], dpi: int) -> None:
    cache = Path(tempfile.gettempdir()) / "quantum-telepathy-matplotlib-cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap

    labels = [result["scenario_id"].replace("_", "\n") for result in results]
    x = np.arange(len(results))
    width = 0.24
    figure, (gap_axis, status_axis) = plt.subplots(
        2, 1, figsize=(13.0, 8.5), gridspec_kw={"height_ratios": (1.05, 1.0)}
    )
    gap_axis.axhline(0.0, color="#333333", linewidth=0.8)
    gap_axis.bar(
        x - width,
        [result["ding_ideal_gap"] for result in results],
        width,
        label="Ding-Jiang ideal",
        color="#3B6EA8",
    )
    gap_axis.bar(
        x,
        [result["li_ideal_gap"] for result in results],
        width,
        label="Li generalized ideal",
        color="#D49A2A",
    )
    gap_axis.bar(
        x + width,
        [result["noisy_gap"] for result in results],
        width,
        label="After physical infidelity",
        color="#498B68",
    )
    gap_axis.set_ylabel("Quantum-classical utility gap")
    gap_axis.set_xticks([])
    gap_axis.legend(ncols=3, loc="upper right")
    gap_axis.grid(axis="y", alpha=0.25)

    criteria = [
        "theoretical_advantage",
        "fidelity_criterion",
        "statistical_certification",
        "rate_criterion",
        "decision_criterion",
        "latency_constrained_regime",
        "overall_operational_quantum_advantage",
    ]
    matrix = np.array([
        [1 if result[criterion] == "PASS" else 0 for result in results]
        for criterion in criteria
    ])
    status_axis.imshow(
        matrix,
        aspect="auto",
        cmap=ListedColormap(["#B94A48", "#3F825B"]),
        vmin=0,
        vmax=1,
    )
    status_axis.set_xticks(x, labels=labels, fontsize=7)
    status_axis.set_yticks(
        np.arange(len(criteria)),
        labels=[criterion.replace("_", " ") for criterion in criteria],
        fontsize=8,
    )
    for row in range(len(criteria)):
        for column in range(len(results)):
            status_axis.text(
                column,
                row,
                "PASS" if matrix[row, column] else "FAIL",
                ha="center",
                va="center",
                color="white",
                fontsize=7,
            )
    status_axis.set_xlabel("Configured research scenario")
    figure.suptitle("Ding-Jiang to Li Operational HFT Waterfall")
    figure.tight_layout()
    figure.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(figure)


def _write_scenario_csv(path: Path, results: list[dict[str, Any]]) -> None:
    fields = (
        "scenario_id",
        "ding_ideal_gap",
        "li_ideal_gap",
        "model_transition_gap_change",
        "epsilon",
        "epsilon_threshold",
        "noisy_gap",
        "physical_gap_retained_fraction",
        "statistics_method",
        "alpha",
        "n_req",
        "p_value_or_bound_at_n_req",
        "t_env",
        "r_req",
        "r_heg",
        "tau_dec",
        "t_loc",
        "t_comm",
        "theoretical_advantage",
        "fidelity_criterion",
        "statistical_certification",
        "rate_criterion",
        "decision_criterion",
        "latency_constrained_regime",
        "overall_operational_quantum_advantage",
        "first_failed_criterion",
        "dominant_bottleneck",
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows({key: result[key] for key in fields} for result in results)


def _write_stage_csv(path: Path, stage_rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in stage_rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(stage_rows)


def analyze(config_path: Path, output_directory: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    hardware_path = (
        config_path.parent / config["hardware_source"]["summary_file"]
    ).resolve()
    hardware = _load_json(hardware_path)
    if hardware["overall_status"] != config["hardware_source"]["required_source_status"]:
        raise RuntimeError("source Table III system calculation is not validated")
    source = config["hardware_source"]
    epsilon = float(_nested(hardware, source["epsilon_path"]))
    r_heg = float(_nested(hardware, source["r_heg_path"]))
    tau_rot = float(_nested(hardware, source["tau_rot_path"]))
    tau_meas = float(_nested(hardware, source["tau_meas_path"]))
    default_t_comm = float(_nested(hardware, source["t_comm_path"]))

    results: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    classical_errors: dict[str, float] = {}
    ding_li_errors: dict[str, float] = {}
    for specification in config["scenarios"]:
        li = specification["li"]
        application = specification["application"]
        distribution = _distribution(li["input_distribution"])
        result = evaluate_hft_waterfall(
            scenario_id=specification["id"],
            ding_p=float(specification["ding"]["p"]),
            ding_beta=float(specification["ding"]["beta"]),
            input_distribution=distribution,
            beta1=float(li["beta1"]),
            beta2=float(li["beta2"]),
            epsilon=epsilon,
            alpha=float(application["alpha"]),
            t_env=float(application["t_env_seconds"]),
            r_heg=r_heg,
            tau_rot=tau_rot,
            tau_meas=tau_meas,
            t_loc=float(application["t_loc_seconds"]),
            t_comm=float(application.get("t_comm_seconds", default_t_comm)),
            statistics_method=specification["statistics_method"],
        )
        serialized = result.to_dict()
        serialized["description"] = specification["description"]
        results.append(serialized)
        stages.extend(
            {"scenario_id": result.scenario_id, **stage}
            for stage in result.stages()
        )
        oracle = enumerated_classical_optimum(
            distribution, float(li["beta1"]), float(li["beta2"])
        )
        classical_errors[result.scenario_id] = abs(
            result.li_classical_value - oracle.value
        )
        ding_distribution = (
            ((1.0 - result.ding_p) ** 2, (1.0 - result.ding_p) * result.ding_p),
            (result.ding_p * (1.0 - result.ding_p), result.ding_p**2),
        )
        if (
            max(
                abs(distribution[x][y] - ding_distribution[x][y])
                for x in range(2)
                for y in range(2)
            )
            <= 1e-12
            and abs(result.beta1 - result.ding_beta) <= 1e-12
            and abs(result.beta2 - result.ding_beta) <= 1e-12
        ):
            ding_li_errors[result.scenario_id] = abs(result.model_transition_gap_change)

    oracle_path = (config_path.parent / config["validation"]["oracle_file"]).resolve()
    oracle = _load_json(oracle_path)
    hardware_expected = oracle["hardware_expected"]
    tolerances = oracle["hardware_absolute_tolerances"]
    validations: dict[str, dict[str, Any]] = {
        "hardware_epsilon": _metric(
            epsilon, hardware_expected["epsilon"], tolerances["epsilon"]
        ),
        "hardware_r_heg": _metric(
            r_heg,
            hardware_expected["r_heg_hz"],
            tolerances["r_heg_hz"],
        ),
        "hardware_tau_dec": _metric(
            tau_rot + tau_meas,
            hardware_expected["tau_dec_seconds"],
            tolerances["tau_dec_seconds"],
        ),
        "classical_enumeration_max_abs_error": _metric(
            max(classical_errors.values()),
            0.0,
            float(config["validation"]["classical_enumeration_absolute_tolerance"]),
        ),
        "ding_li_equivalence_max_abs_error": _metric(
            max(ding_li_errors.values()),
            0.0,
            float(config["validation"]["ding_li_equivalence_absolute_tolerance"]),
        ),
    }
    indexed = {result["scenario_id"]: result for result in results}
    scenario_validations: dict[str, dict[str, Any]] = {}
    for scenario_id, expected in oracle["scenarios"].items():
        actual = indexed[scenario_id]
        comparisons = {
            key: (
                actual["overall_operational_quantum_advantage"]
                if key == "overall_status"
                else actual[key]
            )
            for key in expected
        }
        scenario_validations[scenario_id] = {
            "actual": comparisons,
            "expected": expected,
            "status": "PASS" if comparisons == expected else "FAIL",
        }

    all_pass = all(item["status"] == "PASS" for item in validations.values()) and all(
        item["status"] == "PASS" for item in scenario_validations.values()
    )
    source_digest = hashlib.sha256(hardware_path.read_bytes()).hexdigest()
    summary = {
        "references": config["references"],
        "hardware_provenance": {
            "source_file": str(hardware_path.relative_to(ROOT)),
            "source_sha256": source_digest,
            "source_status": hardware["overall_status"],
            "epsilon": epsilon,
            "r_heg_hz": r_heg,
            "tau_rot_seconds": tau_rot,
            "tau_meas_seconds": tau_meas,
            "default_t_comm_seconds": default_t_comm,
        },
        "scenario_count": len(results),
        "overall_pass_count": sum(
            result["overall_operational_quantum_advantage"] == "PASS" for result in results
        ),
        "overall_fail_count": sum(
            result["overall_operational_quantum_advantage"] == "FAIL" for result in results
        ),
        "results": results,
        "classical_enumeration_abs_errors": classical_errors,
        "ding_li_equivalence_abs_errors": ding_li_errors,
        "validations": validations,
        "scenario_validations": scenario_validations,
        "overall_status": "PASS" if all_pass else "FAIL",
        "research_scope": (
            "Configuration-driven two-party HFT and HFT-style sensitivity analysis; "
            "asymmetric cases are not empirical market calibrations."
        ),
        "notes": config["notes"],
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    _write_scenario_csv(output_directory / "hft_waterfall_scenarios.csv", results)
    _write_stage_csv(output_directory / "hft_waterfall_stages.csv", stages)
    _render_plot(
        output_directory / "hft_waterfall.png",
        results,
        int(config["plot"]["dpi"]),
    )
    with (output_directory / "hft_waterfall_summary.json").open(
        "w", encoding="utf-8"
    ) as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    summary = analyze(arguments.config.resolve(), arguments.output.resolve())
    print(
        json.dumps(
            {
                "overall_status": summary["overall_status"],
                "scenario_count": summary["scenario_count"],
                "overall_pass_count": summary["overall_pass_count"],
                "overall_fail_count": summary["overall_fail_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
