"""Ding-Jiang v3 Type II quantum-memory rate model from Section 4.2."""

from __future__ import annotations

import math
from dataclasses import dataclass


def _validate_positive(value: float, name: str) -> None:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")


def _validate_probability(value: float, name: str) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")


@dataclass(frozen=True)
class TypeIIMemoryParameters:
    """Parameters for the traversal-dominated Type II estimate in paper v3."""

    separation_km: float
    fiber_speed_m_s: float
    herald_speed_m_s: float
    attenuation_db_per_km: float
    projection_success_probability: float
    collection_efficiency: float
    detector_efficiency: float
    memory_count: int = 1

    def __post_init__(self) -> None:
        _validate_positive(self.separation_km, "separation_km")
        _validate_positive(self.fiber_speed_m_s, "fiber_speed_m_s")
        _validate_positive(self.herald_speed_m_s, "herald_speed_m_s")
        if (
            not math.isfinite(self.attenuation_db_per_km)
            or self.attenuation_db_per_km < 0.0
        ):
            raise ValueError("attenuation_db_per_km must be finite and nonnegative")
        _validate_probability(
            self.projection_success_probability,
            "projection_success_probability",
        )
        _validate_probability(self.collection_efficiency, "collection_efficiency")
        _validate_probability(self.detector_efficiency, "detector_efficiency")
        if isinstance(self.memory_count, bool) or not isinstance(self.memory_count, int):
            raise TypeError("memory_count must be an integer")
        if self.memory_count < 1:
            raise ValueError("memory_count must be positive")


@dataclass(frozen=True)
class TypeIIMemoryRate:
    """Decomposed Type II rate quantities for traceable validation."""

    attempt_time_s: float
    per_arm_transmission: float
    joint_two_arm_transmission: float
    success_probability: float
    per_memory_rate_hz: float
    effective_rate_hz: float
    memory_count: int


def traversal_attempt_time_s(
    separation_km: float,
    fiber_speed_m_s: float,
    herald_speed_m_s: float,
) -> float:
    """Return ``d/(2 v_f) + d/(2 v_s)`` from Ding-Jiang v3 Section 4.2."""

    _validate_positive(separation_km, "separation_km")
    _validate_positive(fiber_speed_m_s, "fiber_speed_m_s")
    _validate_positive(herald_speed_m_s, "herald_speed_m_s")
    separation_m = separation_km * 1_000.0
    return separation_m / (2.0 * fiber_speed_m_s) + separation_m / (
        2.0 * herald_speed_m_s
    )


def per_arm_fiber_transmission(
    separation_km: float,
    attenuation_db_per_km: float,
) -> float:
    """Return transmission over one of the two ``d/2`` fiber arms."""

    _validate_positive(separation_km, "separation_km")
    if not math.isfinite(attenuation_db_per_km) or attenuation_db_per_km < 0.0:
        raise ValueError("attenuation_db_per_km must be finite and nonnegative")
    return 10.0 ** (-0.1 * attenuation_db_per_km * separation_km / 2.0)


def heralded_success_probability(
    separation_km: float,
    attenuation_db_per_km: float,
    projection_success_probability: float,
    collection_efficiency: float,
    detector_efficiency: float,
) -> float:
    """Return ``p_p p_c p_d (10^(-0.1 alpha d/2))^2`` from paper v3."""

    _validate_probability(
        projection_success_probability,
        "projection_success_probability",
    )
    _validate_probability(collection_efficiency, "collection_efficiency")
    _validate_probability(detector_efficiency, "detector_efficiency")
    arm_transmission = per_arm_fiber_transmission(
        separation_km,
        attenuation_db_per_km,
    )
    return (
        projection_success_probability
        * collection_efficiency
        * detector_efficiency
        * arm_transmission**2
    )


def type_ii_memory_rate(parameters: TypeIIMemoryParameters) -> TypeIIMemoryRate:
    """Evaluate the v3 Type II estimate ``r_e = M p_s / t_a``."""

    attempt_time = traversal_attempt_time_s(
        parameters.separation_km,
        parameters.fiber_speed_m_s,
        parameters.herald_speed_m_s,
    )
    arm_transmission = per_arm_fiber_transmission(
        parameters.separation_km,
        parameters.attenuation_db_per_km,
    )
    success_probability = heralded_success_probability(
        parameters.separation_km,
        parameters.attenuation_db_per_km,
        parameters.projection_success_probability,
        parameters.collection_efficiency,
        parameters.detector_efficiency,
    )
    per_memory_rate = success_probability / attempt_time
    return TypeIIMemoryRate(
        attempt_time_s=attempt_time,
        per_arm_transmission=arm_transmission,
        joint_two_arm_transmission=arm_transmission**2,
        success_probability=success_probability,
        per_memory_rate_hz=per_memory_rate,
        effective_rate_hz=parameters.memory_count * per_memory_rate,
        memory_count=parameters.memory_count,
    )


def minimum_memory_count_for_rate(
    target_rate_hz: float,
    per_memory_rate_hz: float,
) -> int:
    """Return the minimum ideal parallel-memory multiplicity for a target rate."""

    if not math.isfinite(target_rate_hz) or target_rate_hz < 0.0:
        raise ValueError("target_rate_hz must be finite and nonnegative")
    _validate_positive(per_memory_rate_hz, "per_memory_rate_hz")
    return math.ceil(target_rate_hz / per_memory_rate_hz)
