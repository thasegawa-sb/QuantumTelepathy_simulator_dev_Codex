"""Reproduce the Ding-Jiang v3 Section 4.1 lossy HFT example."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from quantum_telepathy.core.xor_game import independent_bernoulli_distribution
from quantum_telepathy.ding_jiang.fig3 import independent_classical_value
from quantum_telepathy.ding_jiang.hft import hedging_utility
from quantum_telepathy.ding_jiang.loss import (
    LossThresholdResult,
    find_loss_threshold,
    lossy_bell_operator,
    lossy_expected_utility,
    optimize_lossy_value,
    schmidt_coefficients,
)

DEFAULT_CONFIG = Path(__file__).with_name("configs") / "loss_example_v3.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "loss_example_v3"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _metric(name: str, actual: float, oracle_data: dict[str, Any]) -> dict[str, Any]:
    oracle = oracle_data["oracles"][name]
    expected = float(oracle["value"])
    tolerance = float(oracle["absolute_tolerance"])
    error = abs(actual - expected)
    return {
        "actual": actual,
        "expected": expected,
        "absolute_error": error,
        "tolerance": tolerance,
        "status": "PASS" if error <= tolerance else "FAIL",
        "provenance": oracle["provenance"],
    }


def _as_fallback(value: list[list[int]]) -> tuple[tuple[int, int], tuple[int, int]]:
    return (
        (int(value[0][0]), int(value[0][1])),
        (int(value[1][0]), int(value[1][1])),
    )


def _write_threshold_trace(path: Path, threshold: LossThresholdResult) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("efficiency", "quantum_value", "advantage"))
        for evaluation in threshold.evaluations:
            writer.writerow(
                (evaluation.efficiency, evaluation.quantum_value, evaluation.advantage)
            )


def reproduce(config_path: Path, output_directory: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    oracle_path = (config_path.parent / config["validation"]["oracle_file"]).resolve()
    oracle_data = _load_json(oracle_path)
    scenario = config["scenario"]
    optimizer = config["optimizer"]
    threshold_config = config["threshold_search"]
    p = float(scenario["p"])
    beta = float(scenario["beta"])
    efficiency = float(scenario["efficiency"])
    distribution = independent_bernoulli_distribution(p)
    utility = hedging_utility(beta)
    classical_value, strategy_count = independent_classical_value(p, beta)

    optimized = optimize_lossy_value(
        distribution,
        utility,
        (efficiency, efficiency),
        grid_size=int(optimizer["grid_size"]),
        local_starts=int(optimizer["local_starts"]),
        optimizer_tolerance=float(optimizer["optimizer_tolerance"]),
    )
    threshold = find_loss_threshold(
        distribution,
        utility,
        classical_value,
        lower_efficiency=float(threshold_config["lower_efficiency"]),
        upper_efficiency=float(threshold_config["upper_efficiency"]),
        efficiency_tolerance=float(threshold_config["efficiency_tolerance"]),
        advantage_tolerance=float(threshold_config["advantage_tolerance"]),
        grid_size=int(threshold_config["grid_size"]),
        local_starts=int(threshold_config["local_starts"]),
        optimizer_tolerance=float(threshold_config["optimizer_tolerance"]),
    )

    paper_strategy = config["paper_rounded_strategy"]
    paper_angles = (
        float(paper_strategy["angles"][0]),
        float(paper_strategy["angles"][1]),
    )
    paper_state = (
        float(paper_strategy["state"][0]),
        float(paper_strategy["state"][1]),
        float(paper_strategy["state"][2]),
        float(paper_strategy["state"][3]),
    )
    paper_fallback = _as_fallback(paper_strategy["fallback_strategy"])
    paper_strategy_value = lossy_expected_utility(
        distribution,
        utility,
        (efficiency, efficiency),
        paper_angles,
        paper_fallback,
        paper_state,
    )

    optimized_state = np.asarray(optimized.state)
    bell_value = float(
        optimized_state
        @ lossy_bell_operator(
            distribution,
            utility,
            optimized.efficiencies,
            optimized.angles,
            optimized.fallback_strategy,
        )
        @ optimized_state
    )
    direct_value = lossy_expected_utility(
        distribution,
        utility,
        optimized.efficiencies,
        optimized.angles,
        optimized.fallback_strategy,
        optimized.state,
    )
    schmidt = schmidt_coefficients(optimized.state)
    validations = {
        "classical_value": _metric("classical_value", classical_value, oracle_data),
        "lossy_quantum_value": _metric(
            "lossy_quantum_value", optimized.value, oracle_data
        ),
        "threshold_efficiency": _metric(
            "threshold_efficiency", threshold.threshold, oracle_data
        ),
        "largest_schmidt_coefficient": _metric(
            "largest_schmidt_coefficient", schmidt[0], oracle_data
        ),
        "smallest_schmidt_coefficient": _metric(
            "smallest_schmidt_coefficient", schmidt[1], oracle_data
        ),
        "paper_rounded_strategy_value": _metric(
            "paper_rounded_strategy_value", paper_strategy_value, oracle_data
        ),
        "bell_direct_abs_error": _metric(
            "bell_direct_abs_error", abs(bell_value - direct_value), oracle_data
        ),
    }
    summary = {
        "reference": config["reference"],
        "configuration": {
            "scenario": scenario,
            "optimizer": optimizer,
            "threshold_search": threshold_config,
        },
        "simulator": {
            "classical_value": classical_value,
            "deterministic_strategy_count": strategy_count,
            "lossy_quantum_value": optimized.value,
            "quantum_advantage_at_configured_efficiency": optimized.value
            - classical_value,
            "threshold_efficiency": threshold.threshold,
            "threshold_bracket": [threshold.lower_bound, threshold.upper_bound],
            "optimized_angles": list(optimized.angles),
            "optimized_fallback_strategy": [
                list(optimized.fallback_strategy[0]),
                list(optimized.fallback_strategy[1]),
            ],
            "optimized_state": list(optimized.state),
            "schmidt_coefficients": list(schmidt),
            "objective_evaluations": optimized.objective_evaluations,
            "threshold_evaluations": len(threshold.evaluations),
            "paper_rounded_strategy_value": paper_strategy_value,
        },
        "validations": validations,
        "overall_status": (
            "PASS"
            if all(result["status"] == "PASS" for result in validations.values())
            else "FAIL"
        ),
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    with (output_directory / "loss_example_summary.json").open(
        "w", encoding="utf-8"
    ) as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    _write_threshold_trace(output_directory / "loss_threshold_trace.csv", threshold)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    summary = reproduce(arguments.config.resolve(), arguments.output_dir.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
