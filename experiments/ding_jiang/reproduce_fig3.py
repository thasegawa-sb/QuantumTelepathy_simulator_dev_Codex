"""Generate Ding-Jiang v3 Figure 3 data, validation report, and plot."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
import warnings
from decimal import Decimal
from pathlib import Path
from typing import Any

from quantum_telepathy.ding_jiang.fig3 import Fig3Point, evaluate_fig3_grid
from quantum_telepathy.ding_jiang.hft import biased_chsh_values

DEFAULT_CONFIG = Path(__file__).with_name("configs") / "fig3_v3.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "fig3_v3"


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


def _point_map(points: tuple[Fig3Point, ...]) -> dict[tuple[float, float], Fig3Point]:
    return {(point.p, point.beta): point for point in points}


def _metric(
    name: str,
    actual: float,
    oracle_data: dict[str, Any],
) -> dict[str, Any]:
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


def _summarize(
    points: tuple[Fig3Point, ...],
    p_values: tuple[float, ...],
    beta_values: tuple[float, ...],
    oracle_data: dict[str, Any],
) -> dict[str, Any]:
    indexed = _point_map(points)
    maximum = max(points, key=lambda point: point.gap)
    classical_error = max(point.classical_oracle_abs_error for point in points)
    symmetry_error = max(
        abs(indexed[(p, beta)].gap - indexed[(p, float(Decimal("1") - Decimal(str(beta))))].gap)
        for p in p_values
        for beta in beta_values
    )
    beta_half_error = max(abs(indexed[(p, 0.5)].gap) for p in p_values)
    theorem_error = 0.0
    for p in p_values:
        point = indexed[(p, 0.0)]
        theorem = biased_chsh_values(p)
        theorem_error = max(
            theorem_error,
            abs(point.classical_value - theorem.classical_value),
            abs(point.quantum_value - theorem.quantum_value),
            abs(point.gap - theorem.gap),
        )

    validations = {
        "maximum_gap": _metric("maximum_gap", maximum.gap, oracle_data),
        "classical_cross_validation_max_abs_error": _metric(
            "classical_cross_validation_max_abs_error", classical_error, oracle_data
        ),
        "beta_symmetry_max_abs_error": _metric(
            "beta_symmetry_max_abs_error", symmetry_error, oracle_data
        ),
        "beta_half_max_abs_gap": _metric(
            "beta_half_max_abs_gap", beta_half_error, oracle_data
        ),
        "beta_zero_theorem_max_abs_error": _metric(
            "beta_zero_theorem_max_abs_error", theorem_error, oracle_data
        ),
    }
    return {
        "grid": {
            "p_count": len(p_values),
            "beta_count": len(beta_values),
            "point_count": len(points),
        },
        "simulator_extrema": {
            "maximum_gap": maximum.gap,
            "maximum_gap_location": {"p": maximum.p, "beta": maximum.beta},
            "minimum_gap": min(point.gap for point in points),
        },
        "validations": validations,
        "overall_status": (
            "PASS"
            if all(result["status"] == "PASS" for result in validations.values())
            else "FAIL"
        ),
    }


def _write_csv(path: Path, points: tuple[Fig3Point, ...]) -> None:
    fieldnames = tuple(Fig3Point.__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for point in points:
            writer.writerow({name: getattr(point, name) for name in fieldnames})


def _render_plot(
    path: Path,
    points: tuple[Fig3Point, ...],
    p_values: tuple[float, ...],
    beta_values: tuple[float, ...],
    cross_section_p: float,
    cross_section_beta: float,
) -> None:
    cache_directory = Path(tempfile.gettempdir()) / "quantum-telepathy-matplotlib-cache"
    cache_directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_directory))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_directory))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    indexed = _point_map(points)
    p_mesh, beta_mesh = np.meshgrid(p_values, beta_values)
    gap_mesh = np.array(
        [[max(0.0, indexed[(p, beta)].gap) for p in p_values] for beta in beta_values]
    )

    figure = plt.figure(figsize=(10.5, 8.5))
    grid = figure.add_gridspec(2, 2, height_ratios=(1.45, 1.0))
    surface_axis = figure.add_subplot(grid[0, :], projection="3d")
    surface = surface_axis.plot_surface(
        p_mesh,
        beta_mesh,
        gap_mesh,
        cmap="viridis",
        linewidth=0,
        antialiased=True,
    )
    surface_axis.set_xlabel("p")
    surface_axis.set_ylabel("beta")
    surface_axis.set_zlabel("Quantum advantage")
    surface_axis.set_title("(a) Ideal hedging-game advantage")
    figure.colorbar(surface, ax=surface_axis, shrink=0.7, pad=0.08)

    beta_axis = figure.add_subplot(grid[1, 0])
    beta_axis.plot(
        beta_values,
        [indexed[(cross_section_p, beta)].gap for beta in beta_values],
        color="#277DA1",
        linewidth=2.0,
    )
    beta_axis.set_xlabel("beta")
    beta_axis.set_ylabel("Quantum advantage")
    beta_axis.set_title(f"(b) p = {cross_section_p:g}")
    beta_axis.grid(alpha=0.25)

    p_axis = figure.add_subplot(grid[1, 1])
    p_axis.plot(
        p_values,
        [indexed[(p, cross_section_beta)].gap for p in p_values],
        color="#F94144",
        linewidth=2.0,
    )
    p_axis.set_xlabel("p")
    p_axis.set_ylabel("Quantum advantage")
    p_axis.set_title(f"(c) beta = {cross_section_beta:g}")
    p_axis.grid(alpha=0.25)

    figure.suptitle("Ding-Jiang arXiv:2407.21723v3 - Figure 3 reproduction")
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
            message=r"^(divide by zero|overflow|invalid value) encountered in dot$",
            category=RuntimeWarning,
            module=r"mpl_toolkits\.mplot3d\.proj3d",
        )
        figure.savefig(
            path,
            dpi=180,
            metadata={
                "Title": "Ding-Jiang v3 Figure 3 reproduction",
                "Source": "arXiv:2407.21723v3, Equation 3.1 and Figure 3",
            },
        )
    plt.close(figure)


def reproduce(
    config_path: Path,
    output_directory: Path,
    *,
    render_plot: bool = True,
) -> dict[str, Any]:
    config = _load_json(config_path)
    oracle_path = (config_path.parent / config["validation"]["oracle_file"]).resolve()
    oracle_data = _load_json(oracle_path)
    p_values = _inclusive_grid(config["input_model"]["p_grid"])
    beta_values = _inclusive_grid(config["utility_model"]["beta_grid"])
    points = evaluate_fig3_grid(
        p_values,
        beta_values,
        classical_tolerance=float(config["validation"]["classical_abs_tolerance"]),
    )
    summary = {
        "reference": config["reference"],
        "configuration": {
            "input_model": config["input_model"],
            "utility_model": config["utility_model"],
            "cross_sections": config["cross_sections"],
            "notes": config["notes"],
        },
        **_summarize(points, p_values, beta_values, oracle_data),
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    _write_csv(output_directory / "fig3_data.csv", points)
    with (output_directory / "fig3_summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if render_plot:
        _render_plot(
            output_directory / "fig3_reproduction.png",
            points,
            p_values,
            beta_values,
            cross_section_p=float(config["cross_sections"]["p"]),
            cross_section_beta=float(config["cross_sections"]["beta"]),
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-plot", action="store_true")
    arguments = parser.parse_args()
    summary = reproduce(
        arguments.config.resolve(),
        arguments.output_dir.resolve(),
        render_plot=not arguments.skip_plot,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
