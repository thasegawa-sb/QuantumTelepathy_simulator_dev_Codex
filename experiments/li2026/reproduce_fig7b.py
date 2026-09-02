"""Reproduce Li et al. v1 Figure 7(b), the three-party XOR gap surface."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from quantum_telepathy.li2026.multiparty import (
    canonical_paper_strategy_bias,
    enumerated_three_party_classical_optimum,
    evaluate_three_party_operational_advantage,
    three_party_fidelity_threshold,
    three_party_game_coefficients,
    three_party_values,
)
from quantum_telepathy.multiparty.xor import optimize_ghz_equatorial_bias


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "experiments/li2026/configs/fig7b_v1.json"
DEFAULT_OUTPUT = ROOT / "experiments/li2026/results/fig7b_v1"


@dataclass(frozen=True)
class Figure7bPoint:
    probability_one: float
    beta: float
    classical_bias: float
    quantum_bias: float
    classical_value: float
    quantum_value: float
    gap: float
    phase_offset: float
    phase_step_1: float
    phase_step_2: float
    phase_step_3: float


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _grid(specification: dict[str, float]) -> tuple[float, ...]:
    start = float(specification["start"])
    stop = float(specification["stop"])
    step = float(specification["step"])
    if step <= 0.0 or stop < start:
        raise ValueError("grid requires positive step and stop >= start")
    count = round((stop - start) / step)
    if not math.isclose(start + count * step, stop, abs_tol=1e-12):
        raise ValueError("grid endpoints must be exactly reachable by the step")
    return tuple(round(start + index * step, 12) for index in range(count + 1))


def _metric(
    actual: float,
    expected: float,
    tolerance: float,
    provenance: str,
) -> dict[str, Any]:
    error = abs(actual - expected)
    return {
        "actual": actual,
        "expected": expected,
        "absolute_error": error,
        "tolerance": tolerance,
        "status": "PASS" if error <= tolerance else "FAIL",
        "provenance": provenance,
    }


def _evaluate_grid(
    probability_values: tuple[float, ...],
    beta_values: tuple[float, ...],
) -> tuple[tuple[Figure7bPoint, ...], dict[str, float]]:
    points: list[Figure7bPoint] = []
    classical_errors: dict[str, float] = {}
    for beta in beta_values:
        for probability in probability_values:
            values = three_party_values(probability, beta)
            oracle = enumerated_three_party_classical_optimum(probability, beta)
            key = f"p={probability:.2f},beta={beta:.2f}"
            classical_errors[key] = abs(values.classical_value - oracle.value)
            points.append(
                Figure7bPoint(
                    probability_one=probability,
                    beta=beta,
                    classical_bias=values.classical_bias,
                    quantum_bias=values.quantum_bias,
                    classical_value=values.classical_value,
                    quantum_value=values.quantum_value,
                    gap=values.gap,
                    phase_offset=values.phase_offset,
                    phase_step_1=values.phase_steps[0],
                    phase_step_2=values.phase_steps[1],
                    phase_step_3=values.phase_steps[2],
                )
            )
    return tuple(points), classical_errors


def _cross_validate_quantum(
    points: list[list[float]],
) -> tuple[list[dict[str, Any]], float]:
    comparisons: list[dict[str, Any]] = []
    maximum_error = 0.0
    for index, (probability, beta) in enumerate(points):
        production = three_party_values(float(probability), float(beta))
        independent = optimize_ghz_equatorial_bias(
            three_party_game_coefficients(float(probability), float(beta)),
            seed=2604 + index,
        )
        error = abs(production.quantum_bias - independent.bias)
        maximum_error = max(maximum_error, error)
        comparisons.append(
            {
                "probability_one": probability,
                "beta": beta,
                "production_quantum_bias": production.quantum_bias,
                "independent_quantum_bias": independent.bias,
                "absolute_error": error,
                "independent_phase_offset": independent.phase_offset,
                "independent_phase_steps": independent.phase_steps,
            }
        )
    return comparisons, maximum_error


def _render_plot(
    path: Path,
    points: tuple[Figure7bPoint, ...],
    probability_values: tuple[float, ...],
    beta_values: tuple[float, ...],
    minimum_gap: float,
    maximum_gap: float,
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
    from matplotlib.colors import LogNorm

    indexed = {
        (point.beta, point.probability_one): point.gap for point in points
    }
    gap = np.array([
        [indexed[(beta, probability)] for probability in probability_values]
        for beta in beta_values
    ])
    displayed = np.ma.masked_less(gap, minimum_gap)
    figure, axis = plt.subplots(figsize=(6.8, 5.4))
    image = axis.imshow(
        displayed,
        origin="lower",
        extent=(
            probability_values[0],
            probability_values[-1],
            beta_values[0],
            beta_values[-1],
        ),
        aspect="auto",
        cmap="magma",
        norm=LogNorm(vmin=minimum_gap, vmax=maximum_gap),
        interpolation="nearest",
    )
    axis.set_xlabel("Bernoulli input probability p")
    axis.set_ylabel("Utility softness beta")
    axis.set_title("Three-party LCTC quantum-classical gap")
    colorbar = figure.colorbar(image, ax=axis)
    colorbar.set_label("Delta omega")
    figure.tight_layout()
    figure.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(figure)


def _write_grid_csv(path: Path, points: tuple[Figure7bPoint, ...]) -> None:
    fields = tuple(Figure7bPoint.__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(point) for point in points)


def _write_cross_validation_csv(
    path: Path,
    comparisons: list[dict[str, Any]],
) -> None:
    fields = (
        "probability_one",
        "beta",
        "production_quantum_bias",
        "independent_quantum_bias",
        "absolute_error",
        "independent_phase_offset",
        "independent_phase_steps",
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(comparisons)


def reproduce(config_path: Path, output_directory: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    probability_values = _grid(config["grid"]["probability_one"])
    beta_values = _grid(config["grid"]["beta"])
    points, classical_errors = _evaluate_grid(probability_values, beta_values)
    cross_validation, maximum_quantum_error = _cross_validate_quantum(
        config["quantum_cross_validation_points"]
    )
    indexed = {
        (point.probability_one, point.beta): point for point in points
    }
    maximum = max(points, key=lambda point: point.gap)
    minimum_gap = min(point.gap for point in points)
    symmetry_error = max(
        abs(
            indexed[(probability, beta)].gap
            - indexed[(round(1.0 - probability, 12), beta)].gap
        )
        for probability in probability_values
        for beta in beta_values
    )
    beta_half_error = max(
        abs(indexed[(probability, 0.5)].gap)
        for probability in probability_values
    )
    input_boundary_error = max(
        abs(indexed[(probability, beta)].gap)
        for probability in (0.0, 1.0)
        for beta in beta_values
    )
    beta_upper_advantage = max(
        indexed[(probability, beta)].gap
        for probability in probability_values
        for beta in beta_values
        if beta >= 0.5
    )

    operational_specification = config["representative_operational_case"]
    operational = evaluate_three_party_operational_advantage(
        probability_one=operational_specification["probability_one"],
        beta=operational_specification["beta"],
        epsilon_ghz=operational_specification["ghz_state_infidelity"],
        epsilon_meas=operational_specification["measurement_infidelity"],
        alpha=operational_specification["target_alpha"],
        t_env=operational_specification["stationary_window_seconds"],
        r_ghz=operational_specification["supplied_ghz_rate_hz"],
        tau_rot=operational_specification["rotation_time_seconds"],
        tau_meas=operational_specification["measurement_time_seconds"],
        t_loc=operational_specification["local_decision_window_seconds"],
        t_comm=operational_specification["communication_time_seconds"],
    )

    oracle_path = (config_path.parent / config["validation"]["oracle_file"]).resolve()
    oracle = _load_json(oracle_path)
    expected = oracle["analytical_values"]
    operational_expected = oracle["operational_values"]
    limit_tolerance = float(config["validation"]["limit_absolute_tolerance"])
    validations = {
        "uniform_classical_value": _metric(
            indexed[(0.5, 0.0)].classical_value,
            expected["uniform_classical_value"],
            limit_tolerance,
            oracle["provenance"]["analytical"],
        ),
        "uniform_quantum_value": _metric(
            indexed[(0.5, 0.0)].quantum_value,
            expected["uniform_quantum_value"],
            limit_tolerance,
            oracle["provenance"]["analytical"],
        ),
        "uniform_gap": _metric(
            maximum.gap,
            expected["uniform_gap"],
            limit_tolerance,
            oracle["provenance"]["analytical"],
        ),
        "canonical_strategy_bias": _metric(
            canonical_paper_strategy_bias(),
            expected["canonical_strategy_bias"],
            limit_tolerance,
            oracle["provenance"]["analytical"],
        ),
        "uniform_infidelity_threshold": _metric(
            three_party_fidelity_threshold(
                indexed[(0.5, 0.0)].classical_value,
                indexed[(0.5, 0.0)].quantum_value,
            ),
            expected["uniform_infidelity_threshold"],
            limit_tolerance,
            oracle["provenance"]["analytical"],
        ),
        "classical_enumeration_max_abs_error": _metric(
            max(classical_errors.values()),
            0.0,
            float(config["validation"]["classical_absolute_tolerance"]),
            oracle["provenance"]["classical"],
        ),
        "quantum_cross_validation_max_abs_error": _metric(
            maximum_quantum_error,
            0.0,
            float(
                config["validation"][
                    "quantum_cross_validation_absolute_tolerance"
                ]
            ),
            oracle["provenance"]["quantum"],
        ),
        "p_reflection_symmetry_max_abs_error": _metric(
            symmetry_error,
            0.0,
            limit_tolerance,
            "Direct p versus 1-p grid comparison",
        ),
        "beta_half_max_abs_gap": _metric(
            beta_half_error,
            0.0,
            limit_tolerance,
            "Li statement that advantage is confined below beta=1/2",
        ),
        "input_boundary_max_abs_gap": _metric(
            input_boundary_error,
            0.0,
            limit_tolerance,
            "Deterministic-input limit",
        ),
        "beta_upper_advantage_violation": _metric(
            max(0.0, beta_upper_advantage),
            0.0,
            limit_tolerance,
            "Li Figure 7(b) beta<1/2 advantage region",
        ),
        "negative_gap_violation": _metric(
            max(0.0, -minimum_gap),
            0.0,
            limit_tolerance,
            "Quantum strategy contains the optimal classical boundary in this family",
        ),
        "operational_combined_infidelity": _metric(
            operational.combined_infidelity,
            operational_expected["combined_infidelity"],
            limit_tolerance,
            "Li Eq. B18",
        ),
        "operational_required_trials": _metric(
            float(operational.n_req),
            float(operational_expected["required_trials"]),
            0.0,
            "Exact Li Eq. 16-17 search",
        ),
        "operational_required_rate": _metric(
            float(operational.r_req),
            operational_expected["required_rate_hz"],
            limit_tolerance,
            "Li Eq. 18",
        ),
    }
    status_validation = {
        "actual": operational.overall_operational_quantum_advantage.value,
        "expected": operational_expected["overall_status"],
        "status": (
            "PASS"
            if operational.overall_operational_quantum_advantage.value
            == operational_expected["overall_status"]
            else "FAIL"
        ),
        "provenance": "Prospective supplied-rate case; Figure 7(e) not reproduced",
    }
    all_pass = all(item["status"] == "PASS" for item in validations.values()) and (
        status_validation["status"] == "PASS"
    )
    summary = {
        "reference": config["reference"],
        "grid": {
            "probability_count": len(probability_values),
            "beta_count": len(beta_values),
            "point_count": len(points),
        },
        "simulator_extrema": {
            "maximum": asdict(maximum),
            "minimum_gap": minimum_gap,
            "positive_gap_above_display_threshold_count": sum(
                point.gap >= config["plot"]["minimum_displayed_gap"]
                for point in points
            ),
        },
        "quantum_cross_validation": cross_validation,
        "representative_operational_case": {
            "configuration": operational_specification,
            "result": operational.to_dict(),
        },
        "validations": validations,
        "operational_status_validation": status_validation,
        "overall_status": "PASS" if all_pass else "FAIL",
        "paper_reproduction_status": "PARTIAL" if all_pass else "FAIL",
        "paper_reproduction_limitation": oracle["provenance"]["paper_limitation"],
        "notes": config["notes"],
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    _write_grid_csv(output_directory / "fig7b_gap.csv", points)
    _write_cross_validation_csv(
        output_directory / "fig7b_quantum_cross_validation.csv",
        cross_validation,
    )
    _render_plot(
        output_directory / "fig7b_reproduction.png",
        points,
        probability_values,
        beta_values,
        float(config["plot"]["minimum_displayed_gap"]),
        float(config["plot"]["maximum_displayed_gap"]),
        int(config["plot"]["dpi"]),
    )
    with (output_directory / "fig7b_summary.json").open(
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
    summary = reproduce(arguments.config.resolve(), arguments.output.resolve())
    print(
        json.dumps(
            {
                "overall_status": summary["overall_status"],
                "paper_reproduction_status": summary["paper_reproduction_status"],
                "point_count": summary["grid"]["point_count"],
                "maximum_gap": summary["simulator_extrema"]["maximum"]["gap"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
