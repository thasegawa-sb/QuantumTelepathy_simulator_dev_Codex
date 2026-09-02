"""Reproduce the Li et al. v1 Table III 50 km system-level benchmark."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from decimal import Decimal, getcontext
from enum import Enum
from pathlib import Path
from typing import Any

from quantum_telepathy.core.xor_game import chsh_values
from quantum_telepathy.hardware.memory_m0_m1_m2 import (
    evaluate_m2_memory_fidelity,
)
from quantum_telepathy.hardware.yb_node import (
    YbSystemLevelParameters,
    evaluate_yb_system_level,
)
from quantum_telepathy.li2026.fidelity import fidelity_threshold
from quantum_telepathy.li2026.operational import (
    CriterionStatus,
    evaluate_operational_advantage_from_error_components,
)


DEFAULT_CONFIG = Path(__file__).with_name("configs") / "table3_50km_v1.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "table3_50km_v1"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def parameters_from_config(config: dict[str, Any]) -> YbSystemLevelParameters:
    device = config["device"]
    network = config["network"]
    return YbSystemLevelParameters(
        internal_cooperativity=device["internal_cooperativity"],
        n_memory_qubits=device["n_memory_qubits"],
        n_channels=device["n_channels"],
        photon_emission_probability=device["photon_emission_probability"],
        photon_pulse_duration=device["photon_pulse_duration_seconds"],
        swap_time=device["swap_time_seconds"],
        rotation_time=device["rotation_time_seconds"],
        measurement_time=device["measurement_time_seconds"],
        reset_time=device["reset_time_seconds"],
        memory_lifetime=device["memory_lifetime_seconds"],
        distance_km=network["distance_km"],
        attenuation_db_per_km=network["attenuation_db_per_km"],
        group_velocity_m_per_s=network["group_velocity_m_per_s"],
        detector_efficiency=device["detector_efficiency"],
        optics_efficiency=network["optics_efficiency"],
        dark_count_rate=network["dark_count_rate_hz"],
        state_infidelity_upper_bound=device["state_infidelity_upper_bound"],
        measurement_infidelity=device["measurement_infidelity"],
        link_transmission_override=network[
            "table_rounded_link_transmission_override"
        ],
        link_latency_override=network[
            "table_rounded_link_latency_seconds_override"
        ],
    )


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _decimal_oracle(config: dict[str, Any]) -> dict[str, float]:
    """Evaluate the equations independently with 60-digit Decimal arithmetic."""

    getcontext().prec = 60
    device = config["device"]
    network = config["network"]
    p_e = _decimal(device["photon_emission_probability"])
    tau_p = _decimal(device["photon_pulse_duration_seconds"])
    tau_swap = _decimal(device["swap_time_seconds"])
    tau_e = 2 * tau_p + tau_swap
    tpi_probability = p_e**2 / 2
    r0 = tpi_probability / tau_e
    transmission = _decimal(
        network["table_rounded_link_transmission_override"]
    )
    p_ent = (
        tpi_probability
        * transmission
        * _decimal(device["detector_efficiency"]) ** 2
        * _decimal(network["optics_efficiency"]) ** 2
    )
    tau_dec = _decimal(device["rotation_time_seconds"]) + _decimal(
        device["measurement_time_seconds"]
    )
    tau_occ = (
        tau_e
        + _decimal(network["table_rounded_link_latency_seconds_override"])
        + tau_dec
        + _decimal(device["reset_time_seconds"])
    )
    gamma_heg = min(
        Decimal(1) / tau_e,
        _decimal(device["n_memory_qubits"]) / tau_occ,
    )
    r_heg = _decimal(device["n_channels"]) * p_ent * gamma_heg
    dark_count_probability = (
        Decimal(4) * tau_p * _decimal(network["dark_count_rate_hz"])
    )
    false_positive_fraction = dark_count_probability / p_ent
    epsilon_s = _decimal(device["state_infidelity_upper_bound"])
    epsilon_meas = _decimal(device["measurement_infidelity"])
    visibility_squared = (Decimal(1) - 2 * epsilon_meas) ** 2
    epsilon = Decimal(1) - (
        Decimal(1) - Decimal(4) * epsilon_s / Decimal(3)
    ) * visibility_squared
    effective_state_error = epsilon_s + Decimal(2) * (
        Decimal(1)
        - (-tau_occ / _decimal(device["memory_lifetime_seconds"])).exp()
    )
    effective_epsilon = Decimal(1) - (
        Decimal(1) - Decimal(4) * effective_state_error / Decimal(3)
    ) * visibility_squared

    return {
        "tpi_success_probability": float(tpi_probability),
        "tau_e_seconds": float(tau_e),
        "intrinsic_heg_rate_hz": float(r0),
        "entanglement_success_probability": float(p_ent),
        "tau_occ_seconds": float(tau_occ),
        "gamma_heg_hz": float(gamma_heg),
        "r_heg_hz": float(r_heg),
        "dark_count_probability_per_attempt": float(dark_count_probability),
        "false_positive_fraction": float(false_positive_fraction),
        "combined_infidelity_upper_bound": float(epsilon),
        "memory_adjusted_state_infidelity_upper_bound": float(
            effective_state_error
        ),
        "memory_adjusted_combined_infidelity_upper_bound": float(
            effective_epsilon
        ),
    }


def _actual_formula_values(result: Any) -> dict[str, float]:
    return {
        "tpi_success_probability": result.tpi_success_probability,
        "tau_e_seconds": result.tau_e,
        "intrinsic_heg_rate_hz": result.intrinsic_heg_rate,
        "entanglement_success_probability": (
            result.entanglement_success_probability
        ),
        "tau_occ_seconds": result.timing.tau_occ,
        "gamma_heg_hz": result.timing.gamma_heg,
        "r_heg_hz": result.rate.r_heg,
        "dark_count_probability_per_attempt": (
            result.dark_count_probability_per_attempt
        ),
        "false_positive_fraction": result.false_positive_fraction,
        "combined_infidelity_upper_bound": result.combined_infidelity_upper_bound,
        "memory_adjusted_state_infidelity_upper_bound": (
            result.memory_adjusted_state_infidelity_upper_bound
        ),
        "memory_adjusted_combined_infidelity_upper_bound": (
            result.memory_adjusted_combined_infidelity_upper_bound
        ),
    }


def _metric(
    actual: float,
    expected: float,
    tolerance: float,
    provenance: str,
) -> dict[str, Any]:
    absolute_error = abs(actual - expected)
    return {
        "actual": actual,
        "expected": expected,
        "absolute_error": absolute_error,
        "relative_error": absolute_error / abs(expected) if expected != 0.0 else None,
        "tolerance": tolerance,
        "status": "PASS" if absolute_error <= tolerance else "FAIL",
        "provenance": provenance,
    }


def _formula_validations(
    config: dict[str, Any],
    result: Any,
) -> dict[str, dict[str, Any]]:
    expected = _decimal_oracle(config)
    actual = _actual_formula_values(result)
    tolerances = config["validation"]["formula_absolute_tolerances"]
    return {
        name: _metric(
            actual[name],
            expected[name],
            float(tolerances[name]),
            "Independent 60-digit Decimal direct evaluation",
        )
        for name in expected
    }


def _paper_validations(
    result: Any,
    oracle: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    actual = {
        "tpi_success_probability": result.tpi_success_probability,
        "tau_e_seconds": result.tau_e,
        "intrinsic_heg_rate_hz": result.intrinsic_heg_rate,
        "attenuation_law_transmission": result.attenuation_law_transmission,
        "entanglement_success_probability": (
            result.entanglement_success_probability
        ),
        "propagation_latency_seconds": result.propagation_latency,
        "tau_dec_seconds": result.tau_dec,
        "tau_occ_seconds": result.timing.tau_occ,
        "false_positive_fraction": result.false_positive_fraction,
        "combined_infidelity_upper_bound": result.combined_infidelity_upper_bound,
        "r_heg_hz": result.rate.r_heg,
    }
    return {
        name: _metric(
            actual[name],
            float(specification["value"]),
            float(specification["absolute_tolerance"]),
            specification["provenance"],
        )
        for name, specification in oracle["paper_values"].items()
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _write_comparison_csv(
    path: Path,
    validations: dict[str, dict[str, Any]],
) -> None:
    fieldnames = (
        "metric",
        "actual",
        "expected",
        "absolute_error",
        "relative_error",
        "tolerance",
        "status",
        "provenance",
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for metric, validation in validations.items():
            writer.writerow({"metric": metric, **validation})


def reproduce(config_path: Path, output_directory: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    oracle_path = (config_path.parent / config["validation"]["oracle_file"]).resolve()
    oracle = _load_json(oracle_path)
    parameters = parameters_from_config(config)
    result = evaluate_yb_system_level(parameters)
    if result.memory_adjusted_combined_infidelity_upper_bound is None:
        raise ArithmeticError("memory-adjusted combined infidelity is out of domain")

    values = chsh_values()
    threshold = fidelity_threshold(values.classical_bias, values.quantum_bias)
    memory = evaluate_m2_memory_fidelity(
        tau_occ=result.timing.tau_occ,
        tau_mem=parameters.memory_lifetime,
        epsilon_s=parameters.state_infidelity_upper_bound,
        epsilon_meas=parameters.measurement_infidelity,
        epsilon_threshold=threshold,
    )
    application = config["application"]
    operational_cases = []
    for t_env in application["stationary_window_seconds"]:
        status = evaluate_operational_advantage_from_error_components(
            classical_bias=values.classical_bias,
            quantum_bias=values.quantum_bias,
            epsilon_s=result.memory_adjusted_state_infidelity_upper_bound,
            epsilon_meas=parameters.measurement_infidelity,
            alpha=application["target_alpha"],
            t_env=t_env,
            r_heg=result.rate.r_heg,
            tau_rot=parameters.rotation_time,
            tau_meas=parameters.measurement_time,
            t_loc=application["local_decision_window_seconds"],
            t_comm=result.tau_link,
        )
        operational_cases.append(status.to_dict())

    formula_validations = _formula_validations(config, result)
    paper_validations = _paper_validations(result, oracle)
    observed_failed_paper_metrics = sorted(
        name
        for name, validation in paper_validations.items()
        if validation["status"] == "FAIL"
    )
    expected_failed_paper_metrics = sorted(oracle["expected_failed_paper_metrics"])
    discrepancy_set_matches_oracle = (
        observed_failed_paper_metrics == expected_failed_paper_metrics
    )
    formula_status = all(
        validation["status"] == "PASS"
        for validation in formula_validations.values()
    )
    operational_status = all(
        case["overall_operational_quantum_advantage"]
        == CriterionStatus.PASS.value
        for case in operational_cases
    )
    internal_status = all(
        (
            formula_status,
            discrepancy_set_matches_oracle,
            memory.fidelity_criterion,
            result.false_positive_model_domain_valid,
            operational_status,
        )
    )
    paper_status = (
        "PASS"
        if all(item["status"] == "PASS" for item in paper_validations.values())
        else "PARTIAL"
    )

    summary = {
        "reference": config["reference"],
        "configuration": {
            "device": config["device"],
            "network": config["network"],
            "game": config["game"],
            "application": config["application"],
            "notes": config["notes"],
        },
        "system_level_result": _json_ready(asdict(result)),
        "memory_fidelity_result": _json_ready(asdict(memory)),
        "operational_cases": operational_cases,
        "formula_validations": formula_validations,
        "paper_validations": paper_validations,
        "observed_failed_paper_metrics": observed_failed_paper_metrics,
        "expected_failed_paper_metrics": expected_failed_paper_metrics,
        "discrepancy_set_matches_oracle": discrepancy_set_matches_oracle,
        "documented_discrepancies": oracle["expected_discrepancies"],
        "overall_status": "PASS" if internal_status else "FAIL",
        "paper_reproduction_status": paper_status if internal_status else "FAIL",
        "paper_reproduction_limitation": (
            "The formula implementation and operational criteria pass. Table III "
            "contains four displayed-value inconsistencies under direct evaluation "
            "of its listed parameters; these are preserved as documented discrepancies."
        ),
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    _write_comparison_csv(
        output_directory / "table3_paper_comparison.csv", paper_validations
    )
    with (output_directory / "table3_summary.json").open(
        "w", encoding="utf-8"
    ) as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
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
