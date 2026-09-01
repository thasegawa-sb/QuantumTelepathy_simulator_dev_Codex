"""Reproduce the Ding-Jiang v3 Section 4.2 Type II memory calculation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from quantum_telepathy.ding_jiang.memory import (
    TypeIIMemoryParameters,
    minimum_memory_count_for_rate,
    type_ii_memory_rate,
)

DEFAULT_CONFIG = Path(__file__).with_name("configs") / "type_ii_memory_v3.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "type_ii_memory_v3"


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


def _parameters(config: dict[str, Any], memory_count: int) -> TypeIIMemoryParameters:
    values = config["parameters"]
    return TypeIIMemoryParameters(
        separation_km=float(values["separation_km"]),
        fiber_speed_m_s=float(values["fiber_speed_m_s"]),
        herald_speed_m_s=float(values["herald_speed_m_s"]),
        attenuation_db_per_km=float(values["attenuation_db_per_km"]),
        projection_success_probability=float(
            values["projection_success_probability"]
        ),
        collection_efficiency=float(values["collection_efficiency"]),
        detector_efficiency=float(values["detector_efficiency"]),
        memory_count=memory_count,
    )


def reproduce(config_path: Path, output_directory: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    oracle_path = (config_path.parent / config["validation"]["oracle_file"]).resolve()
    oracle_data = _load_json(oracle_path)
    sweep = config["sweep"]
    target_rate = float(config["demand"]["target_event_rate_hz"])
    base_result = type_ii_memory_rate(_parameters(config, 1))
    required_memories = minimum_memory_count_for_rate(
        target_rate,
        base_result.per_memory_rate_hz,
    )

    validations = {
        "attempt_time_formula_s": _metric(
            "attempt_time_formula_s", base_result.attempt_time_s, oracle_data
        ),
        "published_attempt_time_us": _metric(
            "published_attempt_time_us",
            base_result.attempt_time_s * 1e6,
            oracle_data,
        ),
        "success_probability_formula": _metric(
            "success_probability_formula",
            base_result.success_probability,
            oracle_data,
        ),
        "published_success_probability": _metric(
            "published_success_probability",
            base_result.success_probability,
            oracle_data,
        ),
        "per_memory_rate_formula_hz": _metric(
            "per_memory_rate_formula_hz",
            base_result.per_memory_rate_hz,
            oracle_data,
        ),
        "published_per_memory_rate_hz": _metric(
            "published_per_memory_rate_hz",
            base_result.per_memory_rate_hz,
            oracle_data,
        ),
        "minimum_memory_count_for_100_hz": _metric(
            "minimum_memory_count_for_100_hz",
            float(required_memories),
            oracle_data,
        ),
    }

    sweep_rows = []
    for memory_count in range(
        int(sweep["minimum_memory_count"]),
        int(sweep["maximum_memory_count"]) + 1,
    ):
        result = type_ii_memory_rate(_parameters(config, memory_count))
        sweep_rows.append(
            {
                "memory_count": memory_count,
                "effective_rate_hz": result.effective_rate_hz,
                "meets_target_event_rate": result.effective_rate_hz >= target_rate,
            }
        )

    summary = {
        "reference": config["reference"],
        "model": config["model"],
        "configuration": {
            "parameters": config["parameters"],
            "demand": config["demand"],
            "sweep": config["sweep"],
        },
        "simulator": {
            "attempt_time_s": base_result.attempt_time_s,
            "attempt_time_us": base_result.attempt_time_s * 1e6,
            "per_arm_transmission": base_result.per_arm_transmission,
            "joint_two_arm_transmission": base_result.joint_two_arm_transmission,
            "success_probability": base_result.success_probability,
            "per_memory_rate_hz": base_result.per_memory_rate_hz,
            "minimum_memory_count_for_target": required_memories,
            "target_event_rate_hz": target_rate,
        },
        "validations": validations,
        "overall_status": (
            "PASS"
            if all(result["status"] == "PASS" for result in validations.values())
            else "FAIL"
        ),
    }

    output_directory.mkdir(parents=True, exist_ok=True)
    with (output_directory / "type_ii_memory_summary.json").open(
        "w", encoding="utf-8"
    ) as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write("\n")
    with (output_directory / "memory_rate_by_count.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=tuple(sweep_rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(sweep_rows)
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
