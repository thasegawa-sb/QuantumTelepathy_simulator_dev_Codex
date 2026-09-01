"""Reproduce Li et al. v1 Figure 2 data, validation report, and plot."""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from quantum_telepathy.core.xor_game import (
    Matrix2x2,
    independent_bernoulli_distribution,
    uniform_distribution,
)
from quantum_telepathy.ding_jiang.hft import ideal_hedging_values
from quantum_telepathy.li2026.fidelity import (
    fidelity_threshold,
    noisy_gap,
    noisy_quantum_value,
)
from quantum_telepathy.li2026.lctc import (
    correlated_input_distribution,
    enumerated_classical_optimum,
    generalized_lctc_values,
)

DEFAULT_CONFIG = Path(__file__).with_name("configs") / "fig2_v1.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "fig2_v1"


@dataclass(frozen=True)
class IdealSurfacePoint:
    panel: str
    input_parameter: str
    input_value: float
    beta1: float
    beta2: float
    classical_bias: float
    quantum_bias: float
    classical_value: float
    quantum_value: float
    gap: float
    classical_oracle_value: float
    classical_oracle_abs_error: float
    deterministic_strategy_count: int


@dataclass(frozen=True)
class NoisyCurvePoint:
    utility_family: str
    beta1: float
    beta2: float
    epsilon: float
    classical_bias: float
    quantum_bias: float
    classical_value: float
    ideal_quantum_value: float
    ideal_gap: float
    noisy_quantum_value: float
    noisy_gap: float
    epsilon_threshold: float


@dataclass(frozen=True)
class ThresholdPoint:
    utility_family: str
    beta1: float
    beta2: float
    ideal_gap: float
    classical_bias: float
    quantum_bias: float
    epsilon_threshold: float


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


def _evaluate_ideal_point(
    panel: str,
    input_parameter: str,
    input_value: float,
    distribution: Matrix2x2,
    beta: float,
) -> IdealSurfacePoint:
    values = generalized_lctc_values(distribution, beta, beta)
    classical_oracle = enumerated_classical_optimum(distribution, beta, beta)
    return IdealSurfacePoint(
        panel=panel,
        input_parameter=input_parameter,
        input_value=input_value,
        beta1=beta,
        beta2=beta,
        classical_bias=values.classical_bias,
        quantum_bias=values.quantum_bias,
        classical_value=values.classical_value,
        quantum_value=values.quantum_value,
        gap=values.gap,
        classical_oracle_value=classical_oracle.value,
        classical_oracle_abs_error=abs(values.classical_value - classical_oracle.value),
        deterministic_strategy_count=classical_oracle.strategy_count,
    )


def _evaluate_surface(
    panel: str,
    input_parameter: str,
    input_values: tuple[float, ...],
    beta_values: tuple[float, ...],
    distribution_factory: Any,
) -> tuple[IdealSurfacePoint, ...]:
    return tuple(
        _evaluate_ideal_point(
            panel,
            input_parameter,
            input_value,
            distribution_factory(input_value),
            beta,
        )
        for beta in beta_values
        for input_value in input_values
    )


def _utility_families(beta1: float) -> tuple[tuple[str, float], ...]:
    return (("symmetric", beta1), ("asymmetric_half", beta1 / 2.0))


def _evaluate_noisy_curves(
    epsilon_values: tuple[float, ...],
    beta1_values: tuple[float, ...],
) -> tuple[NoisyCurvePoint, ...]:
    distribution = uniform_distribution()
    points: list[NoisyCurvePoint] = []
    for beta1 in beta1_values:
        for family, beta2 in _utility_families(beta1):
            values = generalized_lctc_values(distribution, beta1, beta2)
            threshold = fidelity_threshold(values.classical_bias, values.quantum_bias)
            if abs(threshold) < 1e-15:
                threshold = 0.0
            for epsilon in epsilon_values:
                points.append(
                    NoisyCurvePoint(
                        utility_family=family,
                        beta1=beta1,
                        beta2=beta2,
                        epsilon=epsilon,
                        classical_bias=values.classical_bias,
                        quantum_bias=values.quantum_bias,
                        classical_value=values.classical_value,
                        ideal_quantum_value=values.quantum_value,
                        ideal_gap=values.gap,
                        noisy_quantum_value=noisy_quantum_value(
                            epsilon, values.quantum_bias
                        ),
                        noisy_gap=noisy_gap(
                            epsilon, values.classical_bias, values.quantum_bias
                        ),
                        epsilon_threshold=threshold,
                    )
                )
    return tuple(points)


def _evaluate_thresholds(
    beta1_values: tuple[float, ...],
) -> tuple[ThresholdPoint, ...]:
    distribution = uniform_distribution()
    points: list[ThresholdPoint] = []
    for beta1 in beta1_values:
        for family, beta2 in _utility_families(beta1):
            values = generalized_lctc_values(distribution, beta1, beta2)
            threshold = fidelity_threshold(values.classical_bias, values.quantum_bias)
            points.append(
                ThresholdPoint(
                    utility_family=family,
                    beta1=beta1,
                    beta2=beta2,
                    ideal_gap=values.gap,
                    classical_bias=values.classical_bias,
                    quantum_bias=values.quantum_bias,
                    epsilon_threshold=0.0 if abs(threshold) < 1e-15 else threshold,
                )
            )
    return tuple(points)


def _metric(name: str, actual: float, oracle_data: dict[str, Any]) -> dict[str, Any]:
    oracle = oracle_data["oracles"][name]
    expected = float(oracle["value"])
    tolerance = float(oracle["absolute_tolerance"])
    absolute_error = abs(actual - expected)
    return {
        "actual": actual,
        "expected": expected,
        "absolute_error": absolute_error,
        "relative_error": absolute_error / abs(expected) if expected != 0.0 else None,
        "tolerance": tolerance,
        "status": "PASS" if absolute_error <= tolerance else "FAIL",
        "provenance": oracle["provenance"],
    }


def _rounded(value: float) -> float:
    return round(value, 12)


def _summarize(
    panel_a: tuple[IdealSurfacePoint, ...],
    panel_b: tuple[IdealSurfacePoint, ...],
    noisy_points: tuple[NoisyCurvePoint, ...],
    threshold_points: tuple[ThresholdPoint, ...],
    p_values: tuple[float, ...],
    p11_values: tuple[float, ...],
    beta_values: tuple[float, ...],
    oracle_data: dict[str, Any],
) -> dict[str, Any]:
    maximum_a = max(panel_a, key=lambda point: point.gap)
    maximum_b = max(panel_b, key=lambda point: point.gap)
    classical_error = max(
        point.classical_oracle_abs_error for point in (*panel_a, *panel_b)
    )
    ding_error = 0.0
    for point in panel_a:
        ding = ideal_hedging_values(point.input_value, point.beta1)
        ding_error = max(
            ding_error,
            abs(point.classical_value - ding.classical_value),
            abs(point.quantum_value - ding.quantum_value),
            abs(point.gap - ding.gap),
        )

    distribution_error = 0.0
    for point in panel_b:
        distribution = correlated_input_distribution(point.input_value)
        distribution_error = max(
            distribution_error,
            abs(sum(sum(row) for row in distribution) - 1.0),
            abs(distribution[1][1] - 2.0 * distribution[0][1]),
            abs(distribution[1][1] - 2.0 * distribution[1][0]),
        )

    beta_half_error = max(
        abs(point.gap)
        for point in (*panel_a, *panel_b)
        if _rounded(point.beta1) == 0.5
    )
    threshold_root_error = max(
        abs(noisy_gap(point.epsilon_threshold, point.classical_bias, point.quantum_bias))
        for point in threshold_points
    )

    grouped_noisy: dict[tuple[str, float], list[NoisyCurvePoint]] = {}
    for point in noisy_points:
        grouped_noisy.setdefault(
            (point.utility_family, _rounded(point.beta1)), []
        ).append(point)
    linearity_error = 0.0
    monotonicity_violation = 0.0
    for points in grouped_noisy.values():
        points.sort(key=lambda point: point.epsilon)
        if len(points) < 3:
            continue
        differences = [
            points[index + 1].noisy_gap - points[index].noisy_gap
            for index in range(len(points) - 1)
        ]
        reference_difference = differences[0]
        linearity_error = max(
            linearity_error,
            max(abs(value - reference_difference) for value in differences),
        )
        monotonicity_violation = max(
            monotonicity_violation,
            max(0.0, max(differences)),
        )

    negative_gap_violation = max(
        0.0,
        -min(point.gap for point in (*panel_a, *panel_b)),
        monotonicity_violation,
    )
    chsh_threshold = next(
        point.epsilon_threshold
        for point in threshold_points
        if point.utility_family == "symmetric" and point.beta1 == 0.0
    )

    validations = {
        "chsh_maximum_gap": _metric(
            "chsh_maximum_gap", maximum_a.gap, oracle_data
        ),
        "chsh_fidelity_threshold": _metric(
            "chsh_fidelity_threshold", chsh_threshold, oracle_data
        ),
        "classical_cross_validation_max_abs_error": _metric(
            "classical_cross_validation_max_abs_error", classical_error, oracle_data
        ),
        "ding_layer_cross_validation_max_abs_error": _metric(
            "ding_layer_cross_validation_max_abs_error", ding_error, oracle_data
        ),
        "correlated_distribution_constraint_max_abs_error": _metric(
            "correlated_distribution_constraint_max_abs_error",
            distribution_error,
            oracle_data,
        ),
        "beta_half_max_abs_gap": _metric(
            "beta_half_max_abs_gap", beta_half_error, oracle_data
        ),
        "threshold_root_max_abs_gap": _metric(
            "threshold_root_max_abs_gap", threshold_root_error, oracle_data
        ),
        "noisy_curve_linearity_max_abs_error": _metric(
            "noisy_curve_linearity_max_abs_error", linearity_error, oracle_data
        ),
        "negative_gap_violation": _metric(
            "negative_gap_violation", negative_gap_violation, oracle_data
        ),
    }
    overall_status = (
        "PASS"
        if all(validation["status"] == "PASS" for validation in validations.values())
        else "FAIL"
    )
    return {
        "grid": {
            "panel_a": {
                "p_count": len(p_values),
                "beta_count": len(beta_values),
                "point_count": len(panel_a),
            },
            "panel_b": {
                "p11_count": len(p11_values),
                "beta_count": len(beta_values),
                "point_count": len(panel_b),
            },
            "panel_c": {
                "curve_point_count": len(noisy_points),
                "threshold_point_count": len(threshold_points),
            },
        },
        "simulator_extrema": {
            "panel_a_maximum_gap": asdict(maximum_a),
            "panel_b_maximum_gap": asdict(maximum_b),
            "panel_a_minimum_gap": min(point.gap for point in panel_a),
            "panel_b_minimum_gap": min(point.gap for point in panel_b),
        },
        "validations": validations,
        "overall_status": overall_status,
        "paper_reproduction_status": "PARTIAL" if overall_status == "PASS" else "FAIL",
        "paper_reproduction_limitation": (
            "Author numerical data for Figure 2 are unavailable; analytical limits, "
            "independent classical enumeration, Ding-layer regression, and internal "
            "equation consistency pass, but pointwise paper-data comparison is not possible."
        ),
    }


def _write_dataclass_csv(path: Path, points: tuple[Any, ...]) -> None:
    if not points:
        raise ValueError("cannot write an empty result set")
    fieldnames = tuple(points[0].__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(point) for point in points)


def _render_plot(
    path: Path,
    panel_a: tuple[IdealSurfacePoint, ...],
    panel_b: tuple[IdealSurfacePoint, ...],
    noisy_points: tuple[NoisyCurvePoint, ...],
    threshold_points: tuple[ThresholdPoint, ...],
    p_values: tuple[float, ...],
    p11_values: tuple[float, ...],
    beta_values: tuple[float, ...],
    minimum_gap: float,
    maximum_gap: float,
    dpi: int,
) -> None:
    cache_directory = Path(tempfile.gettempdir()) / "quantum-telepathy-matplotlib-cache"
    cache_directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_directory))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_directory))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import LogNorm

    def gap_mesh(
        points: tuple[IdealSurfacePoint, ...], input_values: tuple[float, ...]
    ) -> Any:
        indexed = {
            (_rounded(point.beta1), _rounded(point.input_value)): point.gap
            for point in points
        }
        raw = np.array(
            [
                [indexed[(_rounded(beta), _rounded(value))] for value in input_values]
                for beta in beta_values
            ]
        )
        return np.ma.masked_less(raw, minimum_gap)

    figure, axes = plt.subplots(1, 3, figsize=(14.2, 4.7), layout="constrained")
    colormap = plt.get_cmap("magma").copy()
    colormap.set_bad("white")
    norm = LogNorm(vmin=minimum_gap, vmax=maximum_gap)
    mesh_a = axes[0].pcolormesh(
        p_values,
        beta_values,
        gap_mesh(panel_a, p_values),
        shading="nearest",
        cmap=colormap,
        norm=norm,
    )
    axes[0].set_xlabel(r"Bernoulli probability $p$")
    axes[0].set_ylabel(r"Utility parameter $\beta$")
    axes[0].set_title("(a) Independent inputs")

    axes[1].pcolormesh(
        p11_values,
        beta_values,
        gap_mesh(panel_b, p11_values),
        shading="nearest",
        cmap=colormap,
        norm=norm,
    )
    axes[1].set_xlabel(r"Correlated probability $P(1,1)$")
    axes[1].set_ylabel(r"Utility parameter $\beta$")
    axes[1].set_title("(b) Correlated inputs")
    colorbar = figure.colorbar(mesh_a, ax=axes[:2], location="bottom", shrink=0.88)
    colorbar.set_label(r"Ideal gap $\Delta\omega$")

    colors = {0.0: "#202020", 0.1: "#0072B2", 0.2: "#D55E00", 0.3: "#009E73"}
    for family, linestyle in (("symmetric", "-"), ("asymmetric_half", "--")):
        for beta1 in sorted({point.beta1 for point in noisy_points}):
            selected = sorted(
                (
                    point
                    for point in noisy_points
                    if point.utility_family == family and point.beta1 == beta1
                ),
                key=lambda point: point.epsilon,
            )
            y_values = [
                point.noisy_gap if point.noisy_gap >= minimum_gap else float("nan")
                for point in selected
            ]
            label = (
                rf"$\beta_1={beta1:g}$, $\beta_2=\beta_1$"
                if family == "symmetric"
                else rf"$\beta_1={beta1:g}$, $\beta_2=\beta_1/2$"
            )
            axes[2].plot(
                [point.epsilon for point in selected],
                y_values,
                color=colors[beta1],
                linestyle=linestyle,
                linewidth=1.7,
                label=label,
            )
    axes[2].set_yscale("log")
    axes[2].set_xlim(0.0, 0.4)
    axes[2].set_ylim(minimum_gap, maximum_gap)
    axes[2].set_xlabel(r"Combined infidelity $\epsilon$")
    axes[2].set_ylabel(r"Noisy gap $\Delta\omega(\epsilon)$")
    axes[2].set_title("(c) Fidelity dependence")
    axes[2].grid(alpha=0.22, which="both")
    axes[2].legend(loc="lower left", fontsize=7.1, frameon=False)

    inset = axes[2].inset_axes([0.53, 0.55, 0.43, 0.4])
    for family, linestyle, color in (
        ("symmetric", "-", "#0072B2"),
        ("asymmetric_half", "--", "#D55E00"),
    ):
        selected = sorted(
            (point for point in threshold_points if point.utility_family == family),
            key=lambda point: point.ideal_gap,
        )
        inset.plot(
            [point.ideal_gap for point in selected],
            [point.epsilon_threshold for point in selected],
            color=color,
            linestyle=linestyle,
            linewidth=1.2,
        )
    inset.set_xlabel(r"$\Delta\omega(0)$", fontsize=7)
    inset.set_ylabel(r"$\epsilon_{\rm th}$", fontsize=7)
    inset.tick_params(labelsize=6.5)
    inset.grid(alpha=0.2)

    figure.suptitle("Li et al. arXiv:2604.07451v1 - Figure 2 reproduction")
    figure.savefig(
        path,
        dpi=dpi,
        metadata={
            "Title": "Li et al. v1 Figure 2 reproduction",
            "Source": "arXiv:2604.07451v1, Figure 2 and Equations 24-37",
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

    p_values = _inclusive_grid(config["panel_a"]["p_grid"])
    p11_values = _inclusive_grid(config["panel_b"]["p11_grid"])
    beta_values = _inclusive_grid(config["panel_a"]["beta_grid"])
    panel_b_beta_values = _inclusive_grid(config["panel_b"]["beta_grid"])
    if beta_values != panel_b_beta_values:
        raise ValueError("Figure 2(a,b) beta grids must match for rendering")
    epsilon_values = _inclusive_grid(config["panel_c"]["epsilon_grid"])
    threshold_beta_values = _inclusive_grid(
        config["panel_c"]["threshold_beta1_grid"]
    )
    beta1_values = tuple(float(value) for value in config["panel_c"]["beta1_values"])

    panel_a = _evaluate_surface(
        "a", "p", p_values, beta_values, independent_bernoulli_distribution
    )
    panel_b = _evaluate_surface(
        "b", "p11", p11_values, beta_values, correlated_input_distribution
    )
    noisy_points = _evaluate_noisy_curves(epsilon_values, beta1_values)
    threshold_points = _evaluate_thresholds(threshold_beta_values)
    summary = {
        "reference": config["reference"],
        "configuration": {
            "panel_a": config["panel_a"],
            "panel_b": config["panel_b"],
            "panel_c": config["panel_c"],
            "plot": config["plot"],
            "notes": config["notes"],
        },
        **_summarize(
            panel_a,
            panel_b,
            noisy_points,
            threshold_points,
            p_values,
            p11_values,
            beta_values,
            oracle_data,
        ),
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    _write_dataclass_csv(output_directory / "fig2a_independent_gap.csv", panel_a)
    _write_dataclass_csv(output_directory / "fig2b_correlated_gap.csv", panel_b)
    _write_dataclass_csv(output_directory / "fig2c_noisy_gap.csv", noisy_points)
    _write_dataclass_csv(output_directory / "fig2c_threshold.csv", threshold_points)
    with (output_directory / "fig2_summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if render_plot:
        _render_plot(
            output_directory / "fig2_reproduction.png",
            panel_a,
            panel_b,
            noisy_points,
            threshold_points,
            p_values,
            p11_values,
            beta_values,
            minimum_gap=float(config["plot"]["minimum_displayed_gap"]),
            maximum_gap=float(config["plot"]["maximum_displayed_gap"]),
            dpi=int(config["plot"]["dpi"]),
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
