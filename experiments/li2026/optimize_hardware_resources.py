"""Run the Phase 13 hardware-resource search and Pareto analysis."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Sequence

from experiments.li2026.reproduce_table3_50km import parameters_from_config
from quantum_telepathy.li2026.operational import CriterionStatus
from quantum_telepathy.optimization.hardware import (
    HardwareCandidateEvaluation,
    HardwareCostVector,
    HardwareImprovementDesign,
    HardwareOptimizationScenario,
    HardwareSearchResult,
    HardwareSearchSpace,
    direct_operational_reevaluation,
    search_hardware_designs,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "experiments/li2026/configs/hardware_optimization_v1.json"
DEFAULT_OUTPUT = ROOT / "experiments/li2026/results/hardware_optimization_v1"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _distribution(raw: list[list[float]]):
    if len(raw) != 2 or any(len(row) != 2 for row in raw):
        raise ValueError("input_distribution must be a 2x2 array")
    return tuple(tuple(float(value) for value in row) for row in raw)


def _scenario(specification: dict[str, Any]) -> HardwareOptimizationScenario:
    application = specification["application"]
    return HardwareOptimizationScenario(
        scenario_id=specification["id"],
        ding_p=specification["ding"]["p"],
        ding_beta=specification["ding"]["beta"],
        input_distribution=_distribution(
            specification["li"]["input_distribution"]
        ),
        beta1=specification["li"]["beta1"],
        beta2=specification["li"]["beta2"],
        statistics_method=specification["statistics_method"],
        alpha=application["alpha"],
        t_env=application["t_env_seconds"],
        t_loc=application["t_loc_seconds"],
    )


def _search_space(specification: dict[str, Any]) -> HardwareSearchSpace:
    order = tuple(HardwareCostVector.__dataclass_fields__)
    weights = specification["cost_weights"]
    if set(weights) != set(order):
        raise ValueError("cost_weights keys do not match HardwareCostVector")
    return HardwareSearchSpace(
        state_infidelity_scales=tuple(
            specification["state_infidelity_scales"]
        ),
        measurement_infidelity_scales=tuple(
            specification["measurement_infidelity_scales"]
        ),
        detector_headroom_fractions=tuple(
            specification["detector_headroom_fractions"]
        ),
        optics_headroom_fractions=tuple(
            specification["optics_headroom_fractions"]
        ),
        decision_time_scales=tuple(specification["decision_time_scales"]),
        memory_lifetime_multipliers=tuple(
            specification["memory_lifetime_multipliers"]
        ),
        n_memory_qubits=tuple(specification["n_memory_qubits"]),
        n_channels=tuple(specification["n_channels"]),
        cost_weights=tuple(float(weights[name]) for name in order),
    )


def _case_id(scenario_id: str, distance_km: float) -> str:
    distance = int(distance_km) if float(distance_km).is_integer() else distance_km
    return f"{scenario_id}@{distance}km"


def _flatten_candidate(candidate: HardwareCandidateEvaluation) -> dict[str, Any]:
    output = candidate.to_dict()
    design = output.pop("design")
    costs = output.pop("cost_vector")
    output.update({f"design_{key}": value for key, value in design.items()})
    output.update({f"cost_{key}": value for key, value in costs.items()})
    output["constraint_violations"] = ";".join(output["constraint_violations"])
    return output


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fields = tuple(rows[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _dominates(
    left: Sequence[float],
    right: Sequence[float],
    tolerance: float,
) -> bool:
    return all(a <= b + tolerance for a, b in zip(left, right, strict=True)) and any(
        a < b - tolerance for a, b in zip(left, right, strict=True)
    )


def _independent_pareto_validation(
    result: HardwareSearchResult,
    tolerance: float,
) -> dict[str, int]:
    feasible = [
        item
        for item in result.candidates
        if item.overall_operational_quantum_advantage is CriterionStatus.PASS
    ]
    front_ids = {item.design for item in result.pareto_front}
    dominated_front_count = 0
    uncovered_feasible_count = 0
    for candidate in result.pareto_front:
        vector = candidate.cost_vector.values()
        if any(
            other.design != candidate.design
            and _dominates(other.cost_vector.values(), vector, tolerance)
            for other in feasible
        ):
            dominated_front_count += 1
    for candidate in feasible:
        if candidate.design in front_ids:
            continue
        if not any(
            _dominates(front.cost_vector.values(), candidate.cost_vector.values(), tolerance)
            for front in result.pareto_front
        ):
            uncovered_feasible_count += 1
    return {
        "dominated_front_count": dominated_front_count,
        "uncovered_feasible_count": uncovered_feasible_count,
    }


def _channel_transition_validation(
    result: HardwareSearchResult,
    baseline_channels: int,
) -> dict[str, Any] | None:
    baseline = result.baseline
    if baseline is None or baseline.r_req is None:
        return None
    other_failures = set(baseline.constraint_violations) - {"rate_criterion"}
    per_channel_rate = baseline.r_heg / baseline_channels
    minimum = math.floor(baseline.r_req / per_channel_rate) + 1
    matching = {
        item.design.n_channels: item
        for item in result.candidates
        if item.design.state_infidelity_scale == 1.0
        and item.design.measurement_infidelity_scale == 1.0
        and item.design.detector_headroom_fraction == 0.0
        and item.design.optics_headroom_fraction == 0.0
        and item.design.decision_time_scale == 1.0
        and item.design.memory_lifetime_multiplier == 1.0
        and item.design.n_memory_qubits == baseline.design.n_memory_qubits
        and item.design.n_channels in {minimum - 1, minimum}
    }
    within_grid = minimum in matching
    transition_passes = (
        within_grid
        and matching[minimum].rate_criterion is CriterionStatus.PASS
        and (
            minimum == baseline_channels
            or matching[minimum - 1].rate_criterion is CriterionStatus.FAIL
        )
    )
    return {
        "minimum_channels_analytical": minimum,
        "per_channel_rate_hz": per_channel_rate,
        "other_baseline_violations": sorted(other_failures),
        "within_search_grid": within_grid,
        "strict_transition_passes": transition_passes,
    }


def _metric(actual: float, expected: float, tolerance: float) -> dict[str, Any]:
    error = abs(actual - expected)
    return {
        "actual": actual,
        "expected": expected,
        "absolute_error": error,
        "tolerance": tolerance,
        "status": "PASS" if error <= tolerance else "FAIL",
    }


def _render_plot(
    path: Path,
    results: list[HardwareSearchResult],
    distance_scenario_id: str,
    dpi: int,
) -> None:
    cache = Path(tempfile.gettempdir()) / "quantum-telepathy-matplotlib-cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    distance_results = sorted(
        (item for item in results if item.scenario_id == distance_scenario_id),
        key=lambda item: item.distance_km,
    )
    distances = np.array([item.distance_km for item in distance_results])
    costs = np.array(
        [
            item.recommended.weighted_cost if item.recommended else np.nan
            for item in distance_results
        ]
    )
    channels = np.array(
        [
            item.recommended.design.n_channels if item.recommended else np.nan
            for item in distance_results
        ]
    )
    state_scales = np.array(
        [
            item.recommended.design.state_infidelity_scale
            if item.recommended
            else np.nan
            for item in distance_results
        ]
    )

    figure, (cost_axis, design_axis) = plt.subplots(2, 1, figsize=(8.2, 7.4))
    cost_axis.plot(distances, costs, "o-", color="#315A7D", label="Minimum effort")
    for item in distance_results:
        if item.recommended is None:
            cost_axis.scatter(
                item.distance_km,
                0.0,
                marker="x",
                s=70,
                color="#B3433F",
                label="Infeasible grid" if "Infeasible grid" not in cost_axis.get_legend_handles_labels()[1] else None,
            )
    cost_axis.set_ylabel("Normalized weighted effort")
    cost_axis.set_title("Operational Hardware Search: Distance Envelope")
    cost_axis.grid(alpha=0.25)
    cost_axis.legend(loc="upper left")

    design_axis.step(
        distances,
        channels,
        where="mid",
        marker="o",
        color="#B06A2B",
        label="Channels",
    )
    design_axis.set_xlabel("Fiber separation (km)")
    design_axis.set_ylabel("Selected channel count", color="#B06A2B")
    design_axis.tick_params(axis="y", labelcolor="#B06A2B")
    design_axis.grid(alpha=0.25)
    scale_axis = design_axis.twinx()
    scale_axis.plot(
        distances,
        state_scales,
        "s--",
        color="#3F7D59",
        label="State-error scale",
    )
    scale_axis.set_ylabel("Selected state-infidelity scale", color="#3F7D59")
    scale_axis.tick_params(axis="y", labelcolor="#3F7D59")
    scale_axis.set_ylim(0.0, 1.05)
    handles_a, labels_a = design_axis.get_legend_handles_labels()
    handles_b, labels_b = scale_axis.get_legend_handles_labels()
    design_axis.legend(handles_a + handles_b, labels_a + labels_b, loc="upper left")
    figure.tight_layout()
    figure.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(figure)


def optimize(config_path: Path, output_directory: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    oracle_path = (config_path.parent / config["validation"]["oracle_file"]).resolve()
    oracle = _load_json(oracle_path)
    baseline_config_path = (
        config_path.parent / config["baseline"]["table3_config_file"]
    ).resolve()
    baseline = parameters_from_config(_load_json(baseline_config_path))
    search_space = _search_space(config["search_space"])
    tolerance = float(config["validation"]["numeric_absolute_tolerance"])
    pareto_tolerance = float(config["validation"]["pareto_tolerance"])

    results: list[HardwareSearchResult] = []
    scenarios: dict[str, HardwareOptimizationScenario] = {}
    descriptions: dict[str, str] = {}
    for specification in config["scenarios"]:
        scenario = _scenario(specification)
        scenarios[scenario.scenario_id] = scenario
        descriptions[scenario.scenario_id] = specification["description"]
        for distance in specification["distances_km"]:
            results.append(
                search_hardware_designs(
                    baseline=baseline,
                    scenario=scenario,
                    distance_km=float(distance),
                    search_space=search_space,
                )
            )

    candidate_rows: list[dict[str, Any]] = []
    pareto_rows: list[dict[str, Any]] = []
    recommended_rows: list[dict[str, Any]] = []
    direct_validations: dict[str, Any] = {}
    pareto_validations: dict[str, Any] = {}
    channel_validations: dict[str, Any] = {}
    case_summaries: list[dict[str, Any]] = []
    propagation_errors: list[float] = []
    direct_numeric_errors: list[float] = []
    direct_status_mismatches = 0
    for result in results:
        case = _case_id(result.scenario_id, result.distance_km)
        for candidate in result.candidates:
            candidate_rows.append({"case_id": case, **_flatten_candidate(candidate)})
        for candidate in result.pareto_front:
            pareto_rows.append({"case_id": case, **_flatten_candidate(candidate)})
        if result.recommended is not None:
            recommended_rows.append(
                {"case_id": case, **_flatten_candidate(result.recommended)}
            )
            direct = direct_operational_reevaluation(
                result.recommended, scenarios[result.scenario_id]
            )
            comparisons = {
                "epsilon": abs(direct.epsilon - result.recommended.epsilon),
                "r_heg": abs(direct.r_heg - result.recommended.r_heg),
                "tau_dec": abs(direct.tau_dec - result.recommended.tau_dec),
                "r_req": abs(direct.r_req - result.recommended.r_req),
            }
            direct_numeric_errors.extend(comparisons.values())
            statuses_match = all(
                getattr(direct, name) is getattr(result.recommended, name)
                for name in (
                    "latency_constrained_regime",
                    "theoretical_advantage",
                    "fidelity_criterion",
                    "statistical_certification",
                    "rate_criterion",
                    "decision_criterion",
                    "overall_operational_quantum_advantage",
                )
            )
            direct_status_mismatches += int(not statuses_match)
            direct_validations[case] = {
                "n_req_matches": direct.n_req == result.recommended.n_req,
                "statuses_match": statuses_match,
                "numeric_absolute_errors": comparisons,
            }
        pareto_validations[case] = _independent_pareto_validation(
            result, pareto_tolerance
        )
        channel = _channel_transition_validation(result, baseline.n_channels)
        if channel is not None:
            channel_validations[case] = channel
        if result.baseline is not None:
            expected_latency = result.distance_km * 1000.0 / baseline.group_velocity_m_per_s
            propagation_errors.append(abs(result.baseline.tau_link - expected_latency))
        case_summaries.append(
            {
                "case_id": case,
                "scenario_id": result.scenario_id,
                "description": descriptions[result.scenario_id],
                "distance_km": result.distance_km,
                "search_status": result.search_status.value,
                "candidate_count": result.candidate_count,
                "evaluated_count": result.evaluated_count,
                "evaluation_error_count": result.evaluation_error_count,
                "certification_limit_count": result.certification_limit_count,
                "feasible_count": result.feasible_count,
                "pareto_count": result.pareto_count,
                "baseline": result.baseline.to_dict() if result.baseline else None,
                "recommended": (
                    result.recommended.to_dict() if result.recommended else None
                ),
            }
        )

    expected_statuses = oracle["expected_search_status"]
    actual_statuses = {
        summary["case_id"]: summary["search_status"] for summary in case_summaries
    }
    distance_oracle = oracle["distance_envelope"]
    distance_results = [
        result
        for result in results
        if result.scenario_id == distance_oracle["scenario_id"]
    ]
    feasible_distances = [
        result.distance_km for result in distance_results if result.feasible_count > 0
    ]
    infeasible_distances = [
        result.distance_km for result in distance_results if result.feasible_count == 0
    ]
    max_feasible = max(feasible_distances) if feasible_distances else None
    first_infeasible = min(infeasible_distances) if infeasible_distances else None
    flat = next(
        result
        for result in results
        if result.scenario_id == "flat_utility_infeasible_control"
    )
    flat_violation = oracle["infeasible_control_required_violation"]

    validations = {
        "case_count": _metric(
            len(results), oracle["expected_case_count"], 0.0
        ),
        "candidate_count_per_case": _metric(
            search_space.candidate_count,
            oracle["expected_candidate_count_per_case"],
            0.0,
        ),
        "search_status_mismatch_count": _metric(
            sum(
                actual_statuses.get(case) != expected
                for case, expected in expected_statuses.items()
            )
            + len(set(actual_statuses) ^ set(expected_statuses)),
            0.0,
            0.0,
        ),
        "evaluation_error_count": _metric(
            sum(result.evaluation_error_count for result in results), 0.0, 0.0
        ),
        "direct_status_mismatch_count": _metric(
            direct_status_mismatches, 0.0, 0.0
        ),
        "direct_numeric_max_abs_error": _metric(
            max(direct_numeric_errors, default=0.0), 0.0, tolerance
        ),
        "propagation_law_max_abs_error": _metric(
            max(propagation_errors, default=0.0), 0.0, tolerance
        ),
        "pareto_dominated_or_uncovered_count": _metric(
            sum(
                value["dominated_front_count"]
                + value["uncovered_feasible_count"]
                for value in pareto_validations.values()
            ),
            0.0,
            0.0,
        ),
        "channel_strict_transition_failure_count": _metric(
            sum(
                not value["strict_transition_passes"]
                for value in channel_validations.values()
                if value["within_search_grid"]
            ),
            0.0,
            0.0,
        ),
        "maximum_configured_feasible_distance_km": _metric(
            max_feasible,
            distance_oracle["maximum_configured_feasible_distance_km"],
            tolerance,
        ),
        "first_configured_infeasible_distance_km": _metric(
            first_infeasible,
            distance_oracle["first_configured_infeasible_distance_km"],
            tolerance,
        ),
        "infeasible_control_violation_count": _metric(
            sum(
                flat_violation not in candidate.constraint_violations
                for candidate in flat.candidates
            ),
            0.0,
            0.0,
        ),
    }
    overall_status = (
        "PASS"
        if all(value["status"] == "PASS" for value in validations.values())
        else "FAIL"
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    _write_csv(output_directory / "hardware_candidates.csv", candidate_rows)
    _write_csv(output_directory / "pareto_front.csv", pareto_rows)
    _write_csv(output_directory / "recommended_designs.csv", recommended_rows)
    _render_plot(
        output_directory / "hardware_optimization.png",
        results,
        distance_oracle["scenario_id"],
        int(config["plot"]["dpi"]),
    )
    summary = {
        "references": config["reference"],
        "research_scope": config["research_scope"],
        "optimization_claim": "Exact only on the configured finite grid; no continuous global optimality claim",
        "cost_interpretation": config["search_space"]["cost_definition"],
        "baseline": {
            "source_config": str(baseline_config_path.relative_to(ROOT)),
            "distance_policy": config["baseline"]["distance_policy"],
            "n_memory_qubits": baseline.n_memory_qubits,
            "n_channels": baseline.n_channels,
            "state_infidelity_upper_bound": baseline.state_infidelity_upper_bound,
            "measurement_infidelity": baseline.measurement_infidelity,
            "rotation_time_seconds": baseline.rotation_time,
            "measurement_time_seconds": baseline.measurement_time,
            "memory_lifetime_seconds": baseline.memory_lifetime,
            "detector_efficiency": baseline.detector_efficiency,
            "optics_efficiency": baseline.optics_efficiency,
        },
        "search_space": {
            **config["search_space"],
            "candidate_count_per_case": search_space.candidate_count,
        },
        "case_count": len(results),
        "cases": case_summaries,
        "distance_envelope": {
            "scenario_id": distance_oracle["scenario_id"],
            "maximum_configured_feasible_distance_km": max_feasible,
            "first_configured_infeasible_distance_km": first_infeasible,
        },
        "direct_reevaluation": direct_validations,
        "independent_pareto_validation": pareto_validations,
        "analytical_channel_transitions": channel_validations,
        "validations": validations,
        "notes": config["notes"],
        "overall_status": overall_status,
    }
    with (output_directory / "hardware_optimization_summary.json").open(
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
    summary = optimize(arguments.config.resolve(), arguments.output.resolve())
    print(f"Overall status: {summary['overall_status']}")
    print(f"Cases: {summary['case_count']}")
    print(
        "Configured distance envelope: "
        f"{summary['distance_envelope']['maximum_configured_feasible_distance_km']} km"
    )


if __name__ == "__main__":
    main()
