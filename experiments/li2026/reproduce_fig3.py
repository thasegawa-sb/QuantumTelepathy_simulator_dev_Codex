"""Reproduce Li et al. v1 Figure 3 finite-statistics rate curves."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

from quantum_telepathy.core.xor_game import chsh_values
from quantum_telepathy.li2026.fidelity import (
    fidelity_threshold,
    noisy_gap,
    noisy_quantum_value,
)
from quantum_telepathy.li2026.statistics import (
    binomial_tail_p_value,
    certification_p_value,
    expected_win_count,
    required_trial_rate,
    required_trials_sequence,
)

DEFAULT_CONFIG = Path(__file__).with_name("configs") / "fig3_v1.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "fig3_v1"


@dataclass(frozen=True)
class RatePoint:
    epsilon: float
    alpha: float
    t_env_seconds: float
    classical_bias: float
    quantum_bias: float
    classical_win_probability: float
    noisy_quantum_win_probability: float
    noisy_gap: float
    epsilon_threshold: float
    required_trials: int
    expected_quantum_wins: int
    certification_p_value: float
    previous_round_p_value: float
    required_rate_hz: float
    required_rate_khz: float
    reference_hardware_rate_hz: float
    reference_hardware_rate_pass: bool


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


def _evaluate_points(config: dict[str, Any]) -> tuple[RatePoint, ...]:
    statistics = config["statistics"]
    epsilon_values = _inclusive_grid(statistics["epsilon_grid"])
    alpha_values = tuple(float(value) for value in statistics["alpha_values"])
    t_env_values = tuple(float(value) for value in statistics["t_env_seconds"])
    reference_rate = float(config["paper_reference_lines"]["heg_rate_hz"])
    values = chsh_values()
    threshold = fidelity_threshold(values.classical_bias, values.quantum_bias)

    points: list[RatePoint] = []
    quantum_probabilities = tuple(
        noisy_quantum_value(epsilon, values.quantum_bias)
        for epsilon in epsilon_values
    )
    for alpha in alpha_values:
        required_counts = required_trials_sequence(
            values.classical_value,
            quantum_probabilities,
            alpha,
            max_rounds=int(statistics["max_rounds"]),
            chunk_size=int(statistics["chunk_size"]),
        )
        for epsilon, quantum_probability, required_count in zip(
            epsilon_values,
            quantum_probabilities,
            required_counts,
            strict=True,
        ):
            expected_wins = expected_win_count(required_count, quantum_probability)
            p_value = binomial_tail_p_value(
                expected_wins,
                required_count,
                values.classical_value,
            )
            previous_p_value = certification_p_value(
                required_count - 1,
                values.classical_value,
                quantum_probability,
            )
            for t_env in t_env_values:
                rate = required_trial_rate(required_count, t_env)
                points.append(
                    RatePoint(
                        epsilon=epsilon,
                        alpha=alpha,
                        t_env_seconds=t_env,
                        classical_bias=values.classical_bias,
                        quantum_bias=values.quantum_bias,
                        classical_win_probability=values.classical_value,
                        noisy_quantum_win_probability=quantum_probability,
                        noisy_gap=noisy_gap(
                            epsilon,
                            values.classical_bias,
                            values.quantum_bias,
                        ),
                        epsilon_threshold=threshold,
                        required_trials=required_count,
                        expected_quantum_wins=expected_wins,
                        certification_p_value=p_value,
                        previous_round_p_value=previous_p_value,
                        required_rate_hz=rate,
                        required_rate_khz=rate / 1000.0,
                        reference_hardware_rate_hz=reference_rate,
                        reference_hardware_rate_pass=reference_rate > rate,
                    )
                )
    return tuple(points)


def _decimal_tail(wins: int, rounds: int, probability: Decimal) -> Decimal:
    return sum(
        Decimal(math.comb(rounds, count))
        * probability**count
        * (Decimal(1) - probability) ** (rounds - count)
        for count in range(wins, rounds + 1)
    )


def _decimal_chsh_oracle(epsilon: float, alpha: float) -> tuple[int, float]:
    getcontext().prec = 60
    epsilon_decimal = Decimal(str(epsilon))
    alpha_decimal = Decimal(str(alpha))
    classical = Decimal(3) / Decimal(4)
    quantum = (
        Decimal(1)
        + (Decimal(1) - epsilon_decimal) / Decimal(2).sqrt()
    ) / Decimal(2)
    for rounds in range(1, 1000):
        wins = int(
            (Decimal(rounds) * quantum).to_integral_value(rounding="ROUND_CEILING")
        )
        p_value = _decimal_tail(wins, rounds, classical)
        if p_value < alpha_decimal:
            return rounds, float(p_value)
    raise ArithmeticError("Decimal oracle search exceeded its small-round limit")


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


def _point_index(points: tuple[RatePoint, ...]) -> dict[tuple[float, float, float], RatePoint]:
    return {
        (round(point.epsilon, 12), point.alpha, point.t_env_seconds): point
        for point in points
    }


def _summarize(
    config: dict[str, Any],
    points: tuple[RatePoint, ...],
    oracle_data: dict[str, Any],
) -> dict[str, Any]:
    indexed = _point_index(points)
    statistics = config["statistics"]
    epsilon_values = _inclusive_grid(statistics["epsilon_grid"])
    alpha_values = tuple(float(value) for value in statistics["alpha_values"])
    t_env_values = tuple(float(value) for value in statistics["t_env_seconds"])
    reference_epsilon = float(
        config["paper_reference_lines"]["combined_infidelity"]
    )
    representative_t_env = t_env_values[0]

    independent_checks: list[dict[str, Any]] = []
    decimal_round_error = 0
    decimal_p_error = 0.0
    for specification in config["validation"]["decimal_oracle_points"]:
        epsilon = float(specification["epsilon"])
        alpha = float(specification["alpha"])
        point = indexed[(round(epsilon, 12), alpha, representative_t_env)]
        oracle_rounds, oracle_p_value = _decimal_chsh_oracle(epsilon, alpha)
        decimal_round_error = max(
            decimal_round_error, abs(point.required_trials - oracle_rounds)
        )
        decimal_p_error = max(
            decimal_p_error, abs(point.certification_p_value - oracle_p_value)
        )
        independent_checks.append(
            {
                "epsilon": epsilon,
                "alpha": alpha,
                "production_required_trials": point.required_trials,
                "decimal_required_trials": oracle_rounds,
                "production_p_value": point.certification_p_value,
                "decimal_p_value": oracle_p_value,
            }
        )

    minimality_violations = sum(
        not (
            indexed[(round(epsilon, 12), alpha, representative_t_env)].certification_p_value
            < alpha
            <= indexed[(round(epsilon, 12), alpha, representative_t_env)].previous_round_p_value
        )
        for alpha in alpha_values
        for epsilon in epsilon_values
    )
    monotonicity_violations = 0
    for alpha in alpha_values:
        counts = [
            indexed[(round(epsilon, 12), alpha, representative_t_env)].required_trials
            for epsilon in epsilon_values
        ]
        monotonicity_violations += sum(
            right < left for left, right in zip(counts, counts[1:])
        )
    for epsilon in epsilon_values:
        loose = indexed[
            (round(epsilon, 12), max(alpha_values), representative_t_env)
        ].required_trials
        strict = indexed[
            (round(epsilon, 12), min(alpha_values), representative_t_env)
        ].required_trials
        monotonicity_violations += strict < loose

    rate_identity_error = max(
        abs(point.required_rate_hz * point.t_env_seconds - point.required_trials)
        for point in points
    )
    reference_points = tuple(
        point for point in points if round(point.epsilon, 12) == reference_epsilon
    )
    reference_hardware_pass_count = sum(
        point.reference_hardware_rate_pass for point in reference_points
    )

    names = {
        (0.0, 0.05): "ideal_alpha_0_05_required_trials",
        (0.0, 0.001): "ideal_alpha_0_001_required_trials",
        (reference_epsilon, 0.05): "epsilon_0_061_alpha_0_05_required_trials",
        (reference_epsilon, 0.001): "epsilon_0_061_alpha_0_001_required_trials",
    }
    validations = {
        name: _metric(
            name,
            indexed[(round(epsilon, 12), alpha, representative_t_env)].required_trials,
            oracle_data,
        )
        for (epsilon, alpha), name in names.items()
    }
    validations.update(
        {
            "decimal_required_trials_max_abs_error": _metric(
                "decimal_required_trials_max_abs_error",
                decimal_round_error,
                oracle_data,
            ),
            "decimal_p_value_max_abs_error": _metric(
                "decimal_p_value_max_abs_error", decimal_p_error, oracle_data
            ),
            "minimality_violation_count": _metric(
                "minimality_violation_count", minimality_violations, oracle_data
            ),
            "monotonicity_violation_count": _metric(
                "monotonicity_violation_count",
                monotonicity_violations,
                oracle_data,
            ),
            "rate_identity_max_abs_error": _metric(
                "rate_identity_max_abs_error", rate_identity_error, oracle_data
            ),
            "reference_hardware_pass_count": _metric(
                "reference_hardware_pass_count",
                reference_hardware_pass_count,
                oracle_data,
            ),
        }
    )
    overall_status = (
        "PASS"
        if all(validation["status"] == "PASS" for validation in validations.values())
        else "FAIL"
    )
    maxima = {
        str(alpha): max(
            indexed[(round(epsilon, 12), alpha, representative_t_env)].required_trials
            for epsilon in epsilon_values
        )
        for alpha in alpha_values
    }
    return {
        "grid": {
            "epsilon_count": len(epsilon_values),
            "alpha_count": len(alpha_values),
            "t_env_count": len(t_env_values),
            "point_count": len(points),
        },
        "simulator_extrema": {
            "maximum_required_trials_by_alpha": maxima,
            "maximum_required_rate_hz": max(point.required_rate_hz for point in points),
        },
        "decimal_oracle_checks": independent_checks,
        "reference_line_points": [asdict(point) for point in reference_points],
        "validations": validations,
        "overall_status": overall_status,
        "paper_reproduction_status": "PARTIAL" if overall_status == "PASS" else "FAIL",
        "paper_reproduction_limitation": (
            "Author numerical data for Figure 3 are unavailable; exact equations, "
            "independent Decimal small-round oracles, discrete minimality, monotonicity, "
            "and paper reference-line behavior pass."
        ),
    }


def _write_csv(path: Path, points: tuple[RatePoint, ...]) -> None:
    fieldnames = tuple(RatePoint.__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(point) for point in points)


def _render_plot(path: Path, config: dict[str, Any], points: tuple[RatePoint, ...]) -> None:
    cache_directory = Path(tempfile.gettempdir()) / "quantum-telepathy-matplotlib-cache"
    cache_directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_directory))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_directory))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    statistics = config["statistics"]
    plot_config = config["plot"]
    threshold = points[0].epsilon_threshold
    reference_epsilon = float(
        config["paper_reference_lines"]["combined_infidelity"]
    )
    reference_rate_khz = (
        float(config["paper_reference_lines"]["heg_rate_hz"]) / 1000.0
    )
    t_env_values = tuple(float(value) for value in statistics["t_env_seconds"])
    alpha_values = tuple(float(value) for value in statistics["alpha_values"])
    colors = {0.001: "#D55E00", 0.1: "#009E73", 10.0: "#0072B2"}
    labels = {0.001: "1 ms", 0.1: "100 ms", 10.0: "10 s"}

    figure, axes = plt.subplots(
        1,
        2,
        figsize=(11.2, 4.5),
        gridspec_kw={"width_ratios": (0.9, 1.55)},
        layout="constrained",
    )

    timeline = axes[0]
    timeline.set_xlim(0.0, 1.0)
    timeline.set_ylim(0.0, 1.0)
    timeline.axis("off")
    timeline.annotate(
        "",
        xy=(0.94, 0.78),
        xytext=(0.08, 0.78),
        arrowprops={"arrowstyle": "->", "linewidth": 1.2, "color": "#202020"},
    )
    timeline.text(0.95, 0.78, "Time", va="center", fontsize=9)
    timeline.plot([0.14, 0.86], [0.9, 0.9], color="#202020", linewidth=1.2)
    timeline.plot([0.14, 0.14], [0.86, 0.94], color="#202020", linewidth=1.2)
    timeline.plot([0.86, 0.86], [0.86, 0.94], color="#202020", linewidth=1.2)
    timeline.text(0.88, 0.9, r"$T_{\rm env}$", va="center", fontsize=10)
    for index, start in enumerate((0.14, 0.34, 0.54, 0.74)):
        color = "#0072B2" if index % 2 == 0 else "#CC79A7"
        timeline.add_patch(
            Rectangle((start, 0.43), 0.11, 0.12, facecolor=color, alpha=0.42, edgecolor=color)
        )
        timeline.plot([start, start], [0.39, 0.59], color="#303030", linewidth=0.8)
    timeline.plot([0.74, 0.85], [0.35, 0.35], color="#202020", linewidth=1.0)
    timeline.plot([0.74, 0.74], [0.31, 0.39], color="#202020", linewidth=1.0)
    timeline.plot([0.85, 0.85], [0.31, 0.39], color="#202020", linewidth=1.0)
    timeline.text(0.87, 0.35, r"$\tau_{\rm dec}$", va="center", fontsize=9)
    timeline.text(
        0.5,
        0.18,
        r"$R_{\rm trial}T_{\rm env}$ usable trials",
        ha="center",
        fontsize=10,
    )
    timeline.set_title("(a) Finite stationary window")

    rate_axis = axes[1]
    for t_env in t_env_values:
        for alpha in alpha_values:
            selected = sorted(
                (
                    point
                    for point in points
                    if point.t_env_seconds == t_env and point.alpha == alpha
                ),
                key=lambda point: point.epsilon,
            )
            rate_axis.plot(
                [point.epsilon for point in selected],
                [point.required_rate_khz for point in selected],
                color=colors[t_env],
                linestyle="-" if alpha == max(alpha_values) else "--",
                linewidth=1.8,
            )
    rate_axis.axhline(reference_rate_khz, color="#707070", linestyle=":", linewidth=1.2)
    rate_axis.axvline(reference_epsilon, color="#707070", linestyle=":", linewidth=1.2)
    rate_axis.set_yscale("log")
    rate_axis.set_xlim(0.0, threshold)
    rate_axis.set_ylim(
        float(plot_config["minimum_rate_khz"]),
        float(plot_config["maximum_rate_khz"]),
    )
    rate_axis.set_xticks((0.0, 0.1, 0.2, threshold), ("0", "0.1", "0.2", r"$\epsilon_{\rm th}$"))
    rate_axis.set_xlabel(r"Combined infidelity $\epsilon$")
    rate_axis.set_ylabel(r"Required rate $R_{\rm req}$ (kHz)")
    rate_axis.set_title("(b) CHSH certification rate")
    rate_axis.grid(alpha=0.2, which="both")
    duration_handles = [
        Line2D([0], [0], color=colors[value], linewidth=1.8, label=rf"$T_{{\rm env}}={labels[value]}$")
        for value in t_env_values
    ]
    style_handles = [
        Line2D([0], [0], color="#303030", linestyle="-", label=r"$\alpha=5\times10^{-2}$"),
        Line2D([0], [0], color="#303030", linestyle="--", label=r"$\alpha=10^{-3}$"),
    ]
    first_legend = rate_axis.legend(
        handles=duration_handles,
        loc="upper left",
        frameon=False,
        fontsize=8,
    )
    rate_axis.add_artist(first_legend)
    rate_axis.legend(handles=style_handles, loc="lower right", frameon=False, fontsize=8)

    figure.suptitle("Li et al. arXiv:2604.07451v1 - Figure 3 reproduction")
    figure.savefig(
        path,
        dpi=int(plot_config["dpi"]),
        metadata={
            "Title": "Li et al. v1 Figure 3 reproduction",
            "Source": "arXiv:2604.07451v1, Figure 3 and Equations 16-18, 39-43",
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
    points = _evaluate_points(config)
    summary = {
        "reference": config["reference"],
        "configuration": {
            "game": config["game"],
            "statistics": config["statistics"],
            "paper_reference_lines": config["paper_reference_lines"],
            "plot": config["plot"],
            "notes": config["notes"],
        },
        **_summarize(config, points, oracle_data),
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    _write_csv(output_directory / "fig3_required_rate.csv", points)
    reference_epsilon = float(
        config["paper_reference_lines"]["combined_infidelity"]
    )
    reference_points = tuple(
        point for point in points if round(point.epsilon, 12) == reference_epsilon
    )
    _write_csv(output_directory / "fig3_reference_points.csv", reference_points)
    with (output_directory / "fig3_summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if render_plot:
        _render_plot(output_directory / "fig3_reproduction.png", config, points)
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
