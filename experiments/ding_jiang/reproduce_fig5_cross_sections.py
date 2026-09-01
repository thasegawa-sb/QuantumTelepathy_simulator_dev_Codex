"""Reproduce Ding-Jiang v3 Figure 5 loss-threshold cross-sections."""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/quantum-telepathy-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/quantum-telepathy-cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from quantum_telepathy.core.xor_game import independent_bernoulli_distribution
from quantum_telepathy.ding_jiang.fig3 import independent_classical_value
from quantum_telepathy.ding_jiang.hft import hedging_utility, ideal_hedging_values
from quantum_telepathy.ding_jiang.loss import find_loss_threshold
from quantum_telepathy.ding_jiang.loss_sdp import find_npa_threshold_lower_bound

DEFAULT_CONFIG = Path(__file__).with_name("configs") / "fig5_cross_sections_v3.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "fig5_cross_sections_v3"


@dataclass(frozen=True)
class ThresholdPoint:
    p: float
    beta: float
    classical_value: float
    ideal_quantum_value: float
    ideal_gap: float
    strategy_transition: float
    strategy_no_advantage_detected_to: float
    strategy_threshold_upper_bound: float
    strategy_evaluations: int
    strategy_runtime_s: float
    npa_threshold_lower_bound: float
    npa_transition_upper_bound: float
    npa_evaluations: int
    npa_runtime_s: float
    npa_inaccurate_solver_calls: int
    numerical_bracket_width: float
    numerical_bracket_order_violation: float


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _metric(name: str, actual: float, oracle_data: dict[str, Any]) -> dict[str, Any]:
    oracle = oracle_data["oracles"][name]
    expected = float(oracle["value"])
    tolerance = float(oracle["absolute_tolerance"])
    absolute_error = abs(actual - expected)
    relative_error = absolute_error / abs(expected) if expected != 0.0 else None
    return {
        "actual": actual,
        "expected": expected,
        "absolute_error": absolute_error,
        "relative_error": relative_error,
        "tolerance": tolerance,
        "status": "PASS" if absolute_error <= tolerance else "FAIL",
        "provenance": oracle["provenance"],
    }


def _compute_point(
    p: float,
    beta: float,
    explicit_config: dict[str, Any],
    npa_config: dict[str, Any],
    explicit_cache: dict[str, Any] | None = None,
) -> ThresholdPoint:
    distribution = independent_bernoulli_distribution(p)
    utility = hedging_utility(beta)
    classical_value, _ = independent_classical_value(p, beta)
    ideal = ideal_hedging_values(p, beta)

    if explicit_cache is None:
        start = perf_counter()
        strategy = find_loss_threshold(
            distribution,
            utility,
            classical_value,
            lower_efficiency=float(explicit_config["lower_efficiency"]),
            upper_efficiency=float(explicit_config["upper_efficiency"]),
            efficiency_tolerance=float(explicit_config["efficiency_tolerance"]),
            advantage_tolerance=float(explicit_config["advantage_tolerance"]),
            grid_size=int(explicit_config["grid_size"]),
            local_starts=int(explicit_config["local_starts"]),
            optimizer_tolerance=float(explicit_config["optimizer_tolerance"]),
        )
        strategy_transition = strategy.threshold
        strategy_lower = strategy.lower_bound
        strategy_upper = strategy.upper_bound
        strategy_evaluations = len(strategy.evaluations)
        strategy_runtime = perf_counter() - start
    else:
        strategy_transition = float(explicit_cache["strategy_transition"])
        strategy_lower = float(explicit_cache["strategy_no_advantage_detected_to"])
        strategy_upper = float(explicit_cache["strategy_threshold_upper_bound"])
        strategy_evaluations = int(explicit_cache["strategy_evaluations"])
        strategy_runtime = float(explicit_cache["strategy_runtime_s"])

    start = perf_counter()
    npa = find_npa_threshold_lower_bound(
        distribution,
        utility,
        classical_value,
        lower_efficiency=float(npa_config["lower_efficiency"]),
        upper_efficiency=float(npa_config["upper_efficiency"]),
        efficiency_tolerance=float(npa_config["efficiency_tolerance"]),
        advantage_tolerance=float(npa_config["advantage_tolerance"]),
        solver=str(npa_config["solver"]),
        solver_tolerance=float(npa_config["solver_tolerance"]),
        solver_error_margin=float(npa_config["solver_error_margin"]),
    )
    npa_runtime = perf_counter() - start
    bracket_width = strategy_upper - npa.threshold_lower_bound
    inaccurate_solver_calls = sum(
        status != "optimal"
        for evaluation in npa.evaluations
        for status in evaluation.solver_statuses
    )

    return ThresholdPoint(
        p=p,
        beta=beta,
        classical_value=classical_value,
        ideal_quantum_value=ideal.quantum_value,
        ideal_gap=ideal.gap,
        strategy_transition=strategy_transition,
        strategy_no_advantage_detected_to=strategy_lower,
        strategy_threshold_upper_bound=strategy_upper,
        strategy_evaluations=strategy_evaluations,
        strategy_runtime_s=strategy_runtime,
        npa_threshold_lower_bound=npa.threshold_lower_bound,
        npa_transition_upper_bound=npa.transition_upper_bound,
        npa_evaluations=len(npa.evaluations),
        npa_runtime_s=npa_runtime,
        npa_inaccurate_solver_calls=inaccurate_solver_calls,
        numerical_bracket_width=max(0.0, bracket_width),
        numerical_bracket_order_violation=max(0.0, -bracket_width),
    )


def _scenario_pairs(config: dict[str, Any]) -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for section in config["cross_sections"]:
        if section["vary"] == "beta":
            pairs.extend((float(section["fixed_p"]), float(value)) for value in section["values"])
        elif section["vary"] == "p":
            pairs.extend((float(value), float(section["fixed_beta"])) for value in section["values"])
        else:
            raise ValueError(f"unsupported cross-section variable: {section['vary']}")
    pairs.extend(
        (float(point["p"]), float(point["beta"]))
        for point in config["benchmark_points"]
    )
    return list(dict.fromkeys(pairs))


def _write_csv(
    path: Path,
    sections: list[dict[str, Any]],
    points: dict[tuple[float, float], ThresholdPoint],
) -> None:
    fieldnames = ["cross_section", "varied_value", *ThresholdPoint.__dataclass_fields__]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for section in sections:
            for value in section["values"]:
                varied_value = float(value)
                pair = (
                    (float(section["fixed_p"]), varied_value)
                    if section["vary"] == "beta"
                    else (varied_value, float(section["fixed_beta"]))
                )
                writer.writerow(
                    {
                        "cross_section": section["name"],
                        "varied_value": varied_value,
                        **asdict(points[pair]),
                    }
                )


def _plot(
    path: Path,
    sections: list[dict[str, Any]],
    points: dict[tuple[float, float], ThresholdPoint],
) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(10.4, 4.2), constrained_layout=True)
    for axis, section in zip(axes, sections, strict=True):
        values = [float(value) for value in section["values"]]
        pairs = [
            (float(section["fixed_p"]), value)
            if section["vary"] == "beta"
            else (value, float(section["fixed_beta"]))
            for value in values
        ]
        lower = [points[pair].npa_threshold_lower_bound for pair in pairs]
        upper = [points[pair].strategy_threshold_upper_bound for pair in pairs]
        axis.fill_between(values, lower, upper, color="#b8d8eb", alpha=0.55)
        axis.plot(values, upper, "o-", color="#16697a", label="Explicit strategy upper bound")
        axis.plot(values, lower, "s--", color="#d1495b", label="NPA Q1+AB lower bound")
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.65, 1.01)
        axis.set_xlabel(r"$\beta$" if section["vary"] == "beta" else r"$p$")
        axis.set_ylabel(r"Threshold efficiency $\eta^*$")
        axis.grid(alpha=0.25)
    axes[0].axhline(2.0 / 3.0, color="#343a40", linestyle=":", label="Analytical 2/3 limit")
    axes[0].set_title(r"(a) $p=0.5$")
    axes[1].set_title(r"(b) $\beta=0.4$")
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside lower center", ncol=3, frameon=False)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _load_explicit_cache(
    path: Path | None,
    config: dict[str, Any],
) -> dict[tuple[float, float], dict[str, Any]]:
    if path is None:
        return {}
    source = _load_json(path)
    expected_explicit_configuration = {
        "cross_sections": config["cross_sections"],
        "benchmark_points": config["benchmark_points"],
        "explicit_strategy_search": config["explicit_strategy_search"],
    }
    source_explicit_configuration = {
        key: source["configuration"][key]
        for key in expected_explicit_configuration
    }
    if source_explicit_configuration != expected_explicit_configuration:
        raise ValueError("reuse summary explicit-strategy config does not match")
    return {
        (float(point["p"]), float(point["beta"])): point
        for point in source["results"]["points"]
    }


def reproduce(
    config_path: Path,
    output_directory: Path,
    reuse_explicit_summary: Path | None = None,
) -> dict[str, Any]:
    config = _load_json(config_path)
    oracle_path = (config_path.parent / config["validation"]["oracle_file"]).resolve()
    oracle_data = _load_json(oracle_path)
    started = perf_counter()
    pairs = _scenario_pairs(config)
    explicit_cache = _load_explicit_cache(reuse_explicit_summary, config)
    points: dict[tuple[float, float], ThresholdPoint] = {}
    for index, pair in enumerate(pairs, start=1):
        points[pair] = _compute_point(
            pair[0],
            pair[1],
            config["explicit_strategy_search"],
            config["npa_search"],
            explicit_cache.get(pair),
        )
        point = points[pair]
        print(
            f"[{index}/{len(pairs)}] p={pair[0]:.3f} beta={pair[1]:.3f} "
            f"NPA-lower={point.npa_threshold_lower_bound:.6f} "
            f"strategy-upper={point.strategy_threshold_upper_bound:.6f}",
            flush=True,
        )

    beta_points = [points[(0.5, float(value))] for value in config["cross_sections"][0]["values"]]
    p_points = [points[(float(value), 0.4)] for value in config["cross_sections"][1]["values"]]
    representative = points[(0.3, 0.3)]
    beta_symmetry_error = max(
        abs(left.strategy_threshold_upper_bound - right.strategy_threshold_upper_bound)
        for left, right in zip(beta_points, reversed(beta_points), strict=True)
    )
    p_symmetry_error = max(
        abs(left.strategy_threshold_upper_bound - right.strategy_threshold_upper_bound)
        for left, right in zip(p_points, reversed(p_points), strict=True)
    )
    order_violation = max(point.numerical_bracket_order_violation for point in points.values())
    validations = {
        "chsh_npa_threshold_beta_0": _metric(
            "chsh_npa_threshold_beta_0",
            beta_points[0].npa_threshold_lower_bound,
            oracle_data,
        ),
        "chsh_npa_threshold_beta_1": _metric(
            "chsh_npa_threshold_beta_1",
            beta_points[-1].npa_threshold_lower_bound,
            oracle_data,
        ),
        "chsh_strategy_upper_excess": _metric(
            "chsh_strategy_upper_excess",
            max(
                beta_points[0].strategy_threshold_upper_bound - 2.0 / 3.0,
                beta_points[-1].strategy_threshold_upper_bound - 2.0 / 3.0,
            ),
            oracle_data,
        ),
        "representative_threshold": _metric(
            "representative_threshold", representative.strategy_transition, oracle_data
        ),
        "beta_symmetry": _metric("beta_symmetry", beta_symmetry_error, oracle_data),
        "p_symmetry_at_beta_0_4": _metric(
            "p_symmetry_at_beta_0_4", p_symmetry_error, oracle_data
        ),
        "numerical_bracket_order_violation": _metric(
            "numerical_bracket_order_violation", order_violation, oracle_data
        ),
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    _write_csv(output_directory / "fig5_cross_sections.csv", config["cross_sections"], points)
    _plot(output_directory / "fig5_cross_sections.png", config["cross_sections"], points)
    summary = {
        "reference": config["reference"],
        "configuration": {
            "cross_sections": config["cross_sections"],
            "benchmark_points": config["benchmark_points"],
            "explicit_strategy_search": config["explicit_strategy_search"],
            "npa_search": config["npa_search"],
        },
        "results": {
            "unique_points": len(points),
            "wall_runtime_s": perf_counter() - started,
            "recorded_point_runtime_s": sum(
                point.strategy_runtime_s + point.npa_runtime_s
                for point in points.values()
            ),
            "explicit_strategy_source": (
                "computed"
                if reuse_explicit_summary is None
                else os.path.relpath(reuse_explicit_summary, Path.cwd())
            ),
            "npa_inaccurate_solver_calls": sum(
                point.npa_inaccurate_solver_calls for point in points.values()
            ),
            "maximum_numerical_bracket_width": max(
                point.numerical_bracket_width for point in points.values()
            ),
            "representative_point": asdict(representative),
            "points": [asdict(points[pair]) for pair in _scenario_pairs(config)],
        },
        "validations": validations,
        "reproduction_status": "PARTIAL",
        "status_reason": (
            "Analytical and published scalar gates pass, but author pointwise Figure 5 data "
            "and the unpublished modified-NPA implementation are unavailable."
        ),
        "overall_status": (
            "PASS"
            if all(validation["status"] == "PASS" for validation in validations.values())
            else "FAIL"
        ),
    }
    with (output_directory / "fig5_cross_sections_summary.json").open(
        "w", encoding="utf-8"
    ) as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--reuse-explicit-summary",
        type=Path,
        help="Reuse explicit-strategy fields from a matching prior summary; NPA is recomputed.",
    )
    arguments = parser.parse_args()
    summary = reproduce(
        arguments.config.resolve(),
        arguments.output_dir.resolve(),
        (
            arguments.reuse_explicit_summary.resolve()
            if arguments.reuse_explicit_summary is not None
            else None
        ),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
