"""Cross-validate Li M2 analytical rates with a seeded event simulation."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scipy.stats import beta, t

from experiments.li2026.reproduce_table3_50km import parameters_from_config
from quantum_telepathy.hardware.event_simulation import (
    M2EventSimulationParameters,
    M2EventSimulationResult,
    simulate_m2_memory_bank,
)
from quantum_telepathy.hardware.yb_node import evaluate_yb_system_level


DEFAULT_CONFIG = (
    Path(__file__).with_name("configs") / "m2_event_cross_validation_v1.json"
)
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "m2_event_cross_validation_v1"


@dataclass(frozen=True)
class ReplicateRecord:
    replicate: int
    seed: int
    attempts_launched: int
    heralded_trials: int
    successful_heralds: int
    memory_releases: int
    memory_wait_launches: int
    emitter_memory_wait_time: float
    attempt_rate: float
    heralded_trial_rate: float
    bell_pair_rate: float
    empirical_success_probability: float
    mean_occupied_memories: float
    occupied_memories_std: float
    peak_occupied_memories: int
    runtime_seconds: float


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _record(index: int, result: M2EventSimulationResult) -> ReplicateRecord:
    if result.empirical_success_probability is None:
        raise ArithmeticError("the measurement window contained no heralded trials")
    return ReplicateRecord(
        replicate=index,
        seed=result.seed,
        attempts_launched=result.attempts_launched,
        heralded_trials=result.heralded_trials,
        successful_heralds=result.successful_heralds,
        memory_releases=result.memory_releases,
        memory_wait_launches=result.memory_wait_launches,
        emitter_memory_wait_time=result.emitter_memory_wait_time,
        attempt_rate=result.attempt_rate,
        heralded_trial_rate=result.heralded_trial_rate,
        bell_pair_rate=result.bell_pair_rate,
        empirical_success_probability=result.empirical_success_probability,
        mean_occupied_memories=result.mean_occupied_memories,
        occupied_memories_std=result.occupied_memories_std,
        peak_occupied_memories=result.peak_occupied_memories,
        runtime_seconds=result.runtime_seconds,
    )


def _mean_std_interval(
    values: list[float],
    confidence_level: float,
) -> dict[str, float | int]:
    count = len(values)
    if count < 2:
        raise ValueError("at least two replicates are required")
    mean = statistics.fmean(values)
    sample_std = statistics.stdev(values)
    standard_error = sample_std / math.sqrt(count)
    critical_value = float(
        t.ppf((1.0 + confidence_level) / 2.0, count - 1)
    )
    half_width = critical_value * standard_error
    return {
        "replicates": count,
        "mean": mean,
        "sample_std": sample_std,
        "standard_error": standard_error,
        "confidence_level": confidence_level,
        "confidence_interval_lower": mean - half_width,
        "confidence_interval_upper": mean + half_width,
        "confidence_interval_half_width": half_width,
    }


def _clopper_pearson_interval(
    successes: int,
    trials: int,
    confidence_level: float,
) -> tuple[float, float]:
    alpha = 1.0 - confidence_level
    lower = (
        0.0
        if successes == 0
        else float(beta.ppf(alpha / 2.0, successes, trials - successes + 1))
    )
    upper = (
        1.0
        if successes == trials
        else float(
            beta.ppf(1.0 - alpha / 2.0, successes + 1, trials - successes)
        )
    )
    return lower, upper


def _relative_validation(
    actual: float,
    expected: float,
    tolerance: float,
) -> dict[str, Any]:
    absolute_error = abs(actual - expected)
    relative_error = absolute_error / abs(expected) if expected != 0.0 else None
    return {
        "actual": actual,
        "expected": expected,
        "absolute_error": absolute_error,
        "relative_error": relative_error,
        "tolerance": tolerance,
        "status": (
            "PASS"
            if relative_error is not None and relative_error <= tolerance
            else "FAIL"
        ),
    }


def _boolean_validation(actual: bool, expected: bool = True) -> dict[str, Any]:
    return {
        "actual": actual,
        "expected": expected,
        "status": "PASS" if actual is expected else "FAIL",
    }


def _write_records(path: Path, records: list[ReplicateRecord]) -> None:
    fieldnames = tuple(ReplicateRecord.__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def _write_trace(path: Path, result: M2EventSimulationResult) -> None:
    fieldnames = (
        "time_seconds",
        "event_type",
        "attempt_id",
        "memory_id",
        "occupied_memories",
        "success",
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for event in result.trace:
            writer.writerow(
                {
                    "time_seconds": event.time,
                    "event_type": event.event_type.value,
                    "attempt_id": event.attempt_id,
                    "memory_id": event.memory_id,
                    "occupied_memories": event.occupied_memories,
                    "success": event.success,
                }
            )


def _write_convergence(path: Path, convergence: list[dict[str, Any]]) -> None:
    fieldnames = tuple(convergence[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(convergence)


def cross_validate(
    config_path: Path,
    output_directory: Path,
) -> dict[str, Any]:
    config = _load_json(config_path)
    hardware_config_path = (
        config_path.parent / config["hardware_config"]
    ).resolve()
    hardware_config = _load_json(hardware_config_path)
    hardware_parameters = parameters_from_config(hardware_config)
    analytical = evaluate_yb_system_level(hardware_parameters)
    simulation = config["simulation"]
    validation_config = config["validation"]

    replicate_count = int(simulation["replicates"])
    if replicate_count < 2:
        raise ValueError("replicates must be at least two")
    confidence_level = float(simulation["confidence_level"])
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be in (0, 1)")
    checkpoints = tuple(int(value) for value in simulation["convergence_checkpoints"])
    if not checkpoints or checkpoints[-1] != replicate_count:
        raise ValueError("the final convergence checkpoint must equal replicates")
    if any(left >= right for left, right in zip(checkpoints, checkpoints[1:])):
        raise ValueError("convergence checkpoints must be strictly increasing")

    records: list[ReplicateRecord] = []
    first_result: M2EventSimulationResult | None = None
    wall_clock_start = time.perf_counter()
    for index in range(replicate_count):
        seed = int(simulation["base_seed"]) + index * int(
            simulation["seed_stride"]
        )
        result = simulate_m2_memory_bank(
            M2EventSimulationParameters(
                tau_e=analytical.tau_e,
                tau_link=analytical.tau_link,
                tau_dec=analytical.tau_dec,
                tau_res=hardware_parameters.reset_time,
                n_memory_qubits=hardware_parameters.n_memory_qubits,
                entanglement_success_probability=(
                    analytical.entanglement_success_probability
                ),
                measurement_duration=simulation[
                    "measurement_duration_seconds"
                ],
                warmup_duration=simulation["warmup_duration_seconds"],
                seed=seed,
                trace_attempts=(
                    simulation["trace_attempts_first_replicate"]
                    if index == 0
                    else 0
                ),
            )
        )
        if index == 0:
            first_result = result
        records.append(_record(index, result))
    total_wall_clock = time.perf_counter() - wall_clock_start
    if first_result is None:
        raise ArithmeticError("no simulation replicate was produced")

    bell_rate_statistics = _mean_std_interval(
        [record.bell_pair_rate for record in records], confidence_level
    )
    attempt_rate_statistics = _mean_std_interval(
        [record.attempt_rate for record in records], confidence_level
    )
    occupancy_statistics = _mean_std_interval(
        [record.mean_occupied_memories for record in records], confidence_level
    )
    runtime_statistics = _mean_std_interval(
        [record.runtime_seconds for record in records], confidence_level
    )

    total_trials = sum(record.heralded_trials for record in records)
    total_successes = sum(record.successful_heralds for record in records)
    observed_success_probability = total_successes / total_trials
    probability_interval = _clopper_pearson_interval(
        total_successes,
        total_trials,
        confidence_level,
    )
    expected_probability = analytical.entanglement_success_probability
    binomial_variance = total_trials * expected_probability * (
        1.0 - expected_probability
    )
    standardized_residual = (
        total_successes - total_trials * expected_probability
    ) / math.sqrt(binomial_variance)
    mean_trials_per_replicate = statistics.fmean(
        record.heralded_trials for record in records
    )
    duration = float(simulation["measurement_duration_seconds"])
    expected_replicate_rate_std = math.sqrt(
        mean_trials_per_replicate
        * expected_probability
        * (1.0 - expected_probability)
    ) / duration
    finite_window_expected_rate = (
        statistics.fmean(record.heralded_trial_rate for record in records)
        * expected_probability
    )
    analytical_mean_occupancy = (
        analytical.timing.gamma_heg * analytical.timing.tau_occ
    )

    convergence: list[dict[str, Any]] = []
    for checkpoint in checkpoints:
        statistics_at_checkpoint = _mean_std_interval(
            [record.bell_pair_rate for record in records[:checkpoint]],
            confidence_level,
        )
        convergence.append(
            {
                "replicates": checkpoint,
                "mean_bell_pair_rate_hz": statistics_at_checkpoint["mean"],
                "sample_std_hz": statistics_at_checkpoint["sample_std"],
                "standard_error_hz": statistics_at_checkpoint["standard_error"],
                "confidence_interval_lower_hz": statistics_at_checkpoint[
                    "confidence_interval_lower"
                ],
                "confidence_interval_upper_hz": statistics_at_checkpoint[
                    "confidence_interval_upper"
                ],
                "confidence_interval_half_width_hz": statistics_at_checkpoint[
                    "confidence_interval_half_width"
                ],
            }
        )

    analytical_inside_interval = (
        bell_rate_statistics["confidence_interval_lower"]
        <= analytical.rate.r_heg
        <= bell_rate_statistics["confidence_interval_upper"]
    )
    finite_window_inside_interval = (
        bell_rate_statistics["confidence_interval_lower"]
        <= finite_window_expected_rate
        <= bell_rate_statistics["confidence_interval_upper"]
    )
    probability_inside_interval = (
        probability_interval[0]
        <= expected_probability
        <= probability_interval[1]
    )
    no_memory_overflow = all(
        record.peak_occupied_memories
        <= hardware_parameters.n_memory_qubits
        for record in records
    )
    decreasing_standard_error = all(
        right["standard_error_hz"] < left["standard_error_hz"]
        for left, right in zip(convergence, convergence[1:])
    )

    validations = {
        "attempt_rate_vs_analytical": _relative_validation(
            attempt_rate_statistics["mean"],
            analytical.timing.gamma_heg,
            float(validation_config["attempt_rate_relative_tolerance"]),
        ),
        "bell_pair_rate_vs_analytical": _relative_validation(
            bell_rate_statistics["mean"],
            analytical.rate.r_heg,
            float(validation_config["bell_pair_rate_relative_tolerance"]),
        ),
        "mean_occupancy_vs_littles_law": {
            "actual": occupancy_statistics["mean"],
            "expected": analytical_mean_occupancy,
            "absolute_error": abs(
                occupancy_statistics["mean"] - analytical_mean_occupancy
            ),
            "tolerance": float(
                validation_config["mean_occupancy_absolute_tolerance"]
            ),
            "status": (
                "PASS"
                if abs(
                    occupancy_statistics["mean"] - analytical_mean_occupancy
                )
                <= float(
                    validation_config["mean_occupancy_absolute_tolerance"]
                )
                else "FAIL"
            ),
        },
        "bell_pair_rate_sample_std_vs_binomial": _relative_validation(
            bell_rate_statistics["sample_std"],
            expected_replicate_rate_std,
            float(validation_config["sample_std_relative_tolerance"]),
        ),
        "analytical_rate_inside_confidence_interval": _boolean_validation(
            analytical_inside_interval,
            bool(
                validation_config[
                    "require_analytical_rate_inside_confidence_interval"
                ]
            ),
        ),
        "finite_window_rate_inside_confidence_interval": _boolean_validation(
            finite_window_inside_interval,
            bool(
                validation_config[
                    "require_finite_window_rate_inside_confidence_interval"
                ]
            ),
        ),
        "success_probability_inside_exact_interval": _boolean_validation(
            probability_inside_interval,
            bool(
                validation_config[
                    "require_success_probability_inside_exact_interval"
                ]
            ),
        ),
        "standardized_binomial_residual": {
            "actual": standardized_residual,
            "maximum_absolute_value": float(
                validation_config["maximum_absolute_standardized_residual"]
            ),
            "status": (
                "PASS"
                if abs(standardized_residual)
                <= float(
                    validation_config["maximum_absolute_standardized_residual"]
                )
                else "FAIL"
            ),
        },
        "memory_capacity_never_exceeded": _boolean_validation(
            no_memory_overflow
        ),
        "standard_error_decreases_at_checkpoints": _boolean_validation(
            decreasing_standard_error,
            bool(validation_config["require_decreasing_standard_error"]),
        ),
    }
    overall_status = (
        "PASS"
        if all(validation["status"] == "PASS" for validation in validations.values())
        else "FAIL"
    )

    summary = {
        "reference": config["reference"],
        "configuration": {
            "hardware_config": config["hardware_config"],
            "simulation": simulation,
            "validation": validation_config,
            "notes": config["notes"],
        },
        "analytical_oracle": {
            "tau_occ_seconds": analytical.timing.tau_occ,
            "attempt_rate_hz": analytical.timing.gamma_heg,
            "entanglement_success_probability": expected_probability,
            "bell_pair_rate_hz": analytical.rate.r_heg,
            "mean_occupied_memories": analytical_mean_occupancy,
            "memory_limited": not analytical.timing.memory_depth_sufficient,
        },
        "occupancy_time_distribution": [
            asdict(item) for item in first_result.occupancy_time_distribution
        ],
        "monte_carlo": {
            "replicates": replicate_count,
            "total_heralded_trials": total_trials,
            "total_successful_heralds": total_successes,
            "observed_success_probability": observed_success_probability,
            "exact_success_probability_interval": {
                "confidence_level": confidence_level,
                "lower": probability_interval[0],
                "upper": probability_interval[1],
            },
            "standardized_binomial_residual": standardized_residual,
            "finite_window_expected_bell_pair_rate_hz": (
                finite_window_expected_rate
            ),
            "expected_replicate_bell_pair_rate_std_hz": (
                expected_replicate_rate_std
            ),
            "bell_pair_rate_statistics": bell_rate_statistics,
            "attempt_rate_statistics": attempt_rate_statistics,
            "occupancy_statistics": occupancy_statistics,
            "runtime_statistics": runtime_statistics,
            "total_wall_clock_seconds": total_wall_clock,
        },
        "convergence": convergence,
        "validations": validations,
        "overall_status": overall_status,
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    _write_records(output_directory / "m2_event_replicates.csv", records)
    _write_trace(output_directory / "m2_event_trace.csv", first_result)
    _write_convergence(
        output_directory / "m2_event_convergence.csv", convergence
    )
    with (output_directory / "m2_event_summary.json").open(
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
    summary = cross_validate(
        arguments.config.resolve(), arguments.output_dir.resolve()
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
