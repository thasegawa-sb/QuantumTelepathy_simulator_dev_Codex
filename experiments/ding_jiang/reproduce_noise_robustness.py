"""Reproduce Ding-Jiang v3 Figures 7-8 depolarizing-noise results."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
import warnings
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from quantum_telepathy.core.xor_game import independent_bernoulli_distribution
from quantum_telepathy.ding_jiang.fig3 import Fig3Point, evaluate_fig3_grid
from quantum_telepathy.ding_jiang.hft import hedging_utility
from quantum_telepathy.ding_jiang.noise import (
    depolarizing_robustness,
    noisy_hedging_gap,
    noisy_hedging_quantum_value,
)

DEFAULT_CONFIG = Path(__file__).with_name("configs") / "noise_robustness_v3.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "noise_robustness_v3"


@dataclass(frozen=True)
class RobustnessRow:
    p: float
    beta: float
    classical_value: float
    quantum_value: float
    ideal_gap: float
    robustness: float
    classical_oracle_abs_error: float


@dataclass(frozen=True)
class NoisyGapRow:
    nu: float
    p: float
    beta: float
    classical_value: float
    noiseless_quantum_value: float
    noisy_quantum_value: float
    signed_noisy_gap: float
    plotted_noisy_gap: float
    theoretical_advantage: bool


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _inclusive_grid(specification: dict[str, float]) -> tuple[float, ...]:
    start = Decimal(str(specification["start"]))
    stop = Decimal(str(specification["stop"]))
    step = Decimal(str(specification["step"]))
    if step <= 0 or stop < start:
        raise ValueError("grid requires step > 0 and stop >= start")
    quotient = (stop - start) / step
    if quotient != quotient.to_integral_value():
        raise ValueError("grid stop must be reachable by an integer number of steps")
    return tuple(float(start + index * step) for index in range(int(quotient) + 1))


def _metric(name: str, actual: float, oracle_data: dict[str, Any]) -> dict[str, Any]:
    oracle = oracle_data["oracles"][name]
    expected = float(oracle["value"])
    tolerance = float(oracle["absolute_tolerance"])
    error = abs(actual - expected)
    return {
        "actual": actual,
        "expected": expected,
        "absolute_error": error,
        "relative_error": error / abs(expected) if expected != 0.0 else None,
        "tolerance": tolerance,
        "status": "PASS" if error <= tolerance else "FAIL",
        "provenance": oracle["provenance"],
    }


def _uniform_output_utility(p: float, beta: float) -> float:
    distribution = independent_bernoulli_distribution(p)
    utility = hedging_utility(beta)
    return sum(
        distribution[x][y] * utility[x][y][a ^ b] / 4.0
        for x in range(2)
        for y in range(2)
        for a in range(2)
        for b in range(2)
    )


def _rows(
    ideal_points: tuple[Fig3Point, ...],
    noise_levels: tuple[float, ...],
    advantage_tolerance: float,
) -> tuple[tuple[RobustnessRow, ...], tuple[NoisyGapRow, ...]]:
    robustness_rows = tuple(
        RobustnessRow(
            p=point.p,
            beta=point.beta,
            classical_value=point.classical_value,
            quantum_value=point.quantum_value,
            ideal_gap=point.gap,
            robustness=depolarizing_robustness(
                point.classical_value,
                point.quantum_value,
                advantage_tolerance=advantage_tolerance,
            ),
            classical_oracle_abs_error=point.classical_oracle_abs_error,
        )
        for point in ideal_points
    )
    noisy_rows = tuple(
        NoisyGapRow(
            nu=nu,
            p=point.p,
            beta=point.beta,
            classical_value=point.classical_value,
            noiseless_quantum_value=point.quantum_value,
            noisy_quantum_value=noisy_hedging_quantum_value(point.quantum_value, nu),
            signed_noisy_gap=noisy_hedging_gap(
                point.classical_value,
                point.quantum_value,
                nu,
            ),
            plotted_noisy_gap=max(
                0.0,
                noisy_hedging_gap(point.classical_value, point.quantum_value, nu),
            ),
            theoretical_advantage=(
                noisy_hedging_gap(point.classical_value, point.quantum_value, nu)
                > advantage_tolerance
            ),
        )
        for nu in noise_levels
        for point in ideal_points
    )
    return robustness_rows, noisy_rows


def _summarize(
    ideal_points: tuple[Fig3Point, ...],
    robustness_rows: tuple[RobustnessRow, ...],
    noisy_rows: tuple[NoisyGapRow, ...],
    noise_specs: list[dict[str, Any]],
    p_values: tuple[float, ...],
    beta_values: tuple[float, ...],
    advantage_tolerance: float,
    oracle_data: dict[str, Any],
) -> dict[str, Any]:
    indexed_robustness = {
        (row.p, row.beta): row.robustness for row in robustness_rows
    }
    maximum = max(robustness_rows, key=lambda row: row.robustness)
    uniform_error = max(
        abs(_uniform_output_utility(point.p, point.beta) - 0.5)
        for point in ideal_points
    )
    classical_error = max(point.classical_oracle_abs_error for point in ideal_points)
    symmetry_error = max(
        abs(
            indexed_robustness[(p, beta)]
            - indexed_robustness[
                (p, float(Decimal("1") - Decimal(str(beta))))
            ]
        )
        for p in p_values
        for beta in beta_values
    )
    zero_gap_robustness = max(
        (
            abs(row.robustness)
            for row in robustness_rows
            if row.ideal_gap <= advantage_tolerance
        ),
        default=0.0,
    )
    threshold_error = max(
        (
            abs(
                noisy_hedging_gap(
                    row.classical_value,
                    row.quantum_value,
                    row.robustness,
                )
            )
            for row in robustness_rows
            if row.robustness > 0.0
        ),
        default=0.0,
    )

    noisy_by_level = {
        float(spec["nu"]): tuple(
            row for row in noisy_rows if row.nu == float(spec["nu"])
        )
        for spec in noise_specs
    }
    positive_sets = [
        {
            (row.p, row.beta)
            for row in noisy_by_level[float(spec["nu"])]
            if row.theoretical_advantage
        }
        for spec in noise_specs
    ]
    nesting_violations = sum(
        len(later - earlier)
        for earlier, later in zip(positive_sets, positive_sets[1:])
    )

    validations = {
        "maximum_robustness": _metric(
            "maximum_robustness", maximum.robustness, oracle_data
        ),
        "published_maximum_robustness": _metric(
            "published_maximum_robustness", maximum.robustness, oracle_data
        ),
        "uniform_baseline_max_abs_error": _metric(
            "uniform_baseline_max_abs_error", uniform_error, oracle_data
        ),
        "classical_cross_validation_max_abs_error": _metric(
            "classical_cross_validation_max_abs_error", classical_error, oracle_data
        ),
        "robustness_beta_symmetry_max_abs_error": _metric(
            "robustness_beta_symmetry_max_abs_error", symmetry_error, oracle_data
        ),
        "zero_gap_robustness_max_abs_value": _metric(
            "zero_gap_robustness_max_abs_value", zero_gap_robustness, oracle_data
        ),
        "threshold_identity_max_abs_error": _metric(
            "threshold_identity_max_abs_error", threshold_error, oracle_data
        ),
        "positive_region_nesting_violations": _metric(
            "positive_region_nesting_violations",
            float(nesting_violations),
            oracle_data,
        ),
    }
    for spec in noise_specs:
        nu = float(spec["nu"])
        key = str(spec["oracle_key"])
        maximum_gap = max(row.plotted_noisy_gap for row in noisy_by_level[nu])
        validations[key] = _metric(key, maximum_gap, oracle_data)

    return {
        "grid": {
            "p_count": len(p_values),
            "beta_count": len(beta_values),
            "robustness_point_count": len(robustness_rows),
            "noisy_gap_point_count": len(noisy_rows),
        },
        "simulator_extrema": {
            "maximum_robustness": maximum.robustness,
            "maximum_robustness_location": {"p": maximum.p, "beta": maximum.beta},
            "maximum_noisy_gap_by_nu": {
                str(spec["nu"]): max(
                    row.plotted_noisy_gap
                    for row in noisy_by_level[float(spec["nu"])]
                )
                for spec in noise_specs
            },
            "positive_point_count_by_nu": {
                str(spec["nu"]): len(positive_sets[index])
                for index, spec in enumerate(noise_specs)
            },
        },
        "validations": validations,
        "overall_status": (
            "PASS"
            if all(result["status"] == "PASS" for result in validations.values())
            else "FAIL"
        ),
    }


def _write_rows(path: Path, rows: tuple[RobustnessRow | NoisyGapRow, ...]) -> None:
    fieldnames = tuple(rows[0].__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def _plot_environment() -> None:
    cache_directory = Path(tempfile.gettempdir()) / "quantum-telepathy-matplotlib-cache"
    cache_directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_directory))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_directory))


def _render_fig7(
    path: Path,
    rows: tuple[RobustnessRow, ...],
    p_values: tuple[float, ...],
    beta_values: tuple[float, ...],
    cross_section_p: float,
    cross_section_beta: float,
) -> None:
    _plot_environment()
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    indexed = {(row.p, row.beta): row for row in rows}
    p_mesh, beta_mesh = np.meshgrid(p_values, beta_values)
    robustness_mesh = np.array(
        [[indexed[(p, beta)].robustness for p in p_values] for beta in beta_values]
    )
    figure = plt.figure(figsize=(10.5, 8.5))
    grid = figure.add_gridspec(2, 2, height_ratios=(1.45, 1.0))
    surface_axis = figure.add_subplot(grid[0, :], projection="3d")
    surface = surface_axis.plot_surface(
        p_mesh, beta_mesh, robustness_mesh, cmap="viridis", linewidth=0
    )
    surface_axis.set_xlabel("p")
    surface_axis.set_ylabel("beta")
    surface_axis.set_zlabel("Robustness")
    surface_axis.set_title("(a) Qubit depolarizing robustness")
    figure.colorbar(surface, ax=surface_axis, shrink=0.7, pad=0.08)

    beta_axis = figure.add_subplot(grid[1, 0])
    beta_axis.plot(
        beta_values,
        [indexed[(cross_section_p, beta)].robustness for beta in beta_values],
        color="#277DA1",
        linewidth=2.0,
    )
    beta_axis.set(xlabel="beta", ylabel="Robustness", title=f"(b) p = {cross_section_p:g}")
    beta_axis.grid(alpha=0.25)

    p_axis = figure.add_subplot(grid[1, 1])
    p_axis.plot(
        p_values,
        [indexed[(p, cross_section_beta)].robustness for p in p_values],
        color="#F94144",
        linewidth=2.0,
    )
    p_axis.set(xlabel="p", ylabel="Robustness", title=f"(c) beta = {cross_section_beta:g}")
    p_axis.grid(alpha=0.25)

    figure.suptitle("Ding-Jiang arXiv:2407.21723v3 - Figure 7 reproduction")
    figure.subplots_adjust(
        left=0.08,
        right=0.92,
        bottom=0.08,
        top=0.91,
        hspace=0.38,
        wspace=0.28,
    )
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=RuntimeWarning,
            module=r"mpl_toolkits\.mplot3d\.proj3d",
        )
        figure.savefig(
            path,
            dpi=180,
            metadata={"Title": "Ding-Jiang v3 Figure 7 reproduction"},
        )
    plt.close(figure)


def _render_fig8(
    path: Path,
    rows: tuple[NoisyGapRow, ...],
    p_values: tuple[float, ...],
    beta_values: tuple[float, ...],
    noise_levels: tuple[float, ...],
) -> None:
    _plot_environment()
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    indexed = {(row.nu, row.p, row.beta): row for row in rows}
    p_mesh, beta_mesh = np.meshgrid(p_values, beta_values)
    figure = plt.figure(figsize=(8.0, 13.0))
    for index, nu in enumerate(noise_levels, start=1):
        axis = figure.add_subplot(len(noise_levels), 1, index, projection="3d")
        gap_mesh = np.array(
            [
                [indexed[(nu, p, beta)].plotted_noisy_gap for p in p_values]
                for beta in beta_values
            ]
        )
        surface = axis.plot_surface(
            p_mesh,
            beta_mesh,
            gap_mesh,
            cmap="viridis",
            linewidth=0,
        )
        axis.set_xlabel("p")
        axis.set_ylabel("beta")
        axis.set_zlabel("Quantum advantage")
        axis.set_title(f"({chr(96 + index)}) nu = {nu:g}")
        figure.colorbar(surface, ax=axis, shrink=0.65, pad=0.08)
    figure.suptitle("Ding-Jiang arXiv:2407.21723v3 - Figure 8 reproduction")
    figure.subplots_adjust(left=0.06, right=0.9, bottom=0.04, top=0.95, hspace=0.24)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=RuntimeWarning,
            module=r"mpl_toolkits\.mplot3d\.proj3d",
        )
        figure.savefig(
            path,
            dpi=180,
            metadata={"Title": "Ding-Jiang v3 Figure 8 reproduction"},
        )
    plt.close(figure)


def reproduce(
    config_path: Path,
    output_directory: Path,
    *,
    render_plots: bool = True,
) -> dict[str, Any]:
    config = _load_json(config_path)
    oracle_path = (config_path.parent / config["validation"]["oracle_file"]).resolve()
    oracle_data = _load_json(oracle_path)
    p_values = _inclusive_grid(config["input_model"]["p_grid"])
    beta_values = _inclusive_grid(config["utility_model"]["beta_grid"])
    noise_specs = config["noise_levels"]
    noise_levels = tuple(float(spec["nu"]) for spec in noise_specs)
    if tuple(sorted(noise_levels)) != noise_levels or len(set(noise_levels)) != len(
        noise_levels
    ):
        raise ValueError("noise levels must be unique and increasing")
    advantage_tolerance = float(config["validation"]["advantage_tolerance"])
    ideal_points = evaluate_fig3_grid(
        p_values,
        beta_values,
        classical_tolerance=float(config["validation"]["classical_abs_tolerance"]),
    )
    robustness_rows, noisy_rows = _rows(
        ideal_points,
        noise_levels,
        advantage_tolerance,
    )
    summary = {
        "reference": config["reference"],
        "model": config["model"],
        "configuration": {
            "input_model": config["input_model"],
            "utility_model": config["utility_model"],
            "noise_levels": noise_specs,
            "cross_sections": config["cross_sections"],
            "notes": config["notes"],
        },
        **_summarize(
            ideal_points,
            robustness_rows,
            noisy_rows,
            noise_specs,
            p_values,
            beta_values,
            advantage_tolerance,
            oracle_data,
        ),
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    _write_rows(output_directory / "fig7_robustness_data.csv", robustness_rows)
    _write_rows(output_directory / "fig8_noisy_gap_data.csv", noisy_rows)
    with (output_directory / "noise_robustness_summary.json").open(
        "w", encoding="utf-8"
    ) as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if render_plots:
        _render_fig7(
            output_directory / "fig7_reproduction.png",
            robustness_rows,
            p_values,
            beta_values,
            float(config["cross_sections"]["p"]),
            float(config["cross_sections"]["beta"]),
        )
        _render_fig8(
            output_directory / "fig8_reproduction.png",
            noisy_rows,
            p_values,
            beta_values,
            noise_levels,
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-plots", action="store_true")
    arguments = parser.parse_args()
    summary = reproduce(
        arguments.config.resolve(),
        arguments.output_dir.resolve(),
        render_plots=not arguments.skip_plots,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
