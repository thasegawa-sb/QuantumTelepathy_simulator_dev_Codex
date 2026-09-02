"""Discrete-event simulation of one Li M2 entanglement-generation channel.

The simulator implements the deterministic resource timing assumed by Li
Eqs. 46-48 and samples each herald outcome independently. All durations use
seconds and rates use inverse seconds.
"""

from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass
from enum import Enum
from numbers import Integral

import numpy as np

from quantum_telepathy.hardware.memory_m0_m1_m2 import occupancy_time


def _finite_nonnegative(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be a finite nonnegative value")
    return result


def _finite_positive(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be a finite positive value")
    return result


def _probability(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be a finite value in [0, 1]")
    return result


def _positive_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return int(value)


def _nonnegative_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return int(value)


class M2EventType(str, Enum):
    """Events exposed in a bounded diagnostic trace."""

    ATTEMPT_START = "ATTEMPT_START"
    HERALD_FAILURE = "HERALD_FAILURE"
    HERALD_SUCCESS = "HERALD_SUCCESS"
    MEMORY_RELEASE = "MEMORY_RELEASE"


@dataclass(frozen=True)
class M2SimulationEvent:
    """One trace event from a selected entanglement-generation attempt."""

    time: float
    event_type: M2EventType
    attempt_id: int
    memory_id: int
    occupied_memories: int | None
    success: bool | None


@dataclass(frozen=True)
class M2EventSimulationParameters:
    """Configuration for one seeded, single-channel M2 simulation run."""

    tau_e: float
    tau_link: float
    tau_dec: float
    tau_res: float
    n_memory_qubits: int
    entanglement_success_probability: float
    measurement_duration: float
    warmup_duration: float
    seed: int
    trace_attempts: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "tau_e", _finite_positive("tau_e", self.tau_e))
        for name in ("tau_link", "tau_dec", "tau_res", "warmup_duration"):
            object.__setattr__(
                self, name, _finite_nonnegative(name, getattr(self, name))
            )
        object.__setattr__(
            self,
            "measurement_duration",
            _finite_positive("measurement_duration", self.measurement_duration),
        )
        object.__setattr__(
            self,
            "n_memory_qubits",
            _positive_integer("n_memory_qubits", self.n_memory_qubits),
        )
        object.__setattr__(
            self,
            "entanglement_success_probability",
            _probability(
                "entanglement_success_probability",
                self.entanglement_success_probability,
            ),
        )
        object.__setattr__(self, "seed", _nonnegative_integer("seed", self.seed))
        object.__setattr__(
            self,
            "trace_attempts",
            _nonnegative_integer("trace_attempts", self.trace_attempts),
        )


@dataclass(frozen=True)
class M2OccupancyTime:
    """Time and fraction spent at one memory-occupancy level."""

    occupied_memories: int
    duration: float
    fraction: float


@dataclass(frozen=True)
class M2EventSimulationResult:
    """Finite-window throughput and time-weighted memory statistics."""

    seed: int
    warmup_duration: float
    measurement_duration: float
    tau_occ: float
    total_attempts_simulated: int
    attempts_launched: int
    heralded_trials: int
    successful_heralds: int
    memory_releases: int
    memory_wait_launches: int
    emitter_memory_wait_time: float
    attempt_rate: float
    heralded_trial_rate: float
    bell_pair_rate: float
    empirical_success_probability: float | None
    mean_occupied_memories: float
    occupied_memories_std: float
    peak_occupied_memories: int
    occupancy_time_distribution: tuple[M2OccupancyTime, ...]
    runtime_seconds: float
    trace: tuple[M2SimulationEvent, ...]


def _interval_overlap(
    left: float,
    right: float,
    window_left: float,
    window_right: float,
) -> float:
    return max(0.0, min(right, window_right) - max(left, window_left))


def simulate_m2_memory_bank(
    parameters: M2EventSimulationParameters,
) -> M2EventSimulationResult:
    """Simulate finite-memory scheduling and Bernoulli herald outcomes.

    The emitter is work-conserving: a new trial starts after ``tau_e`` when a
    memory is free, or immediately when the next memory is released if all
    memories are occupied. The measurement interval is half-open after a
    configurable warmup period.
    """

    runtime_start = time.perf_counter()
    tau_occ = occupancy_time(
        parameters.tau_e,
        parameters.tau_link,
        parameters.tau_dec,
        parameters.tau_res,
    )
    measurement_start = parameters.warmup_duration
    measurement_end = measurement_start + parameters.measurement_duration
    herald_delay = parameters.tau_e + parameters.tau_link
    rng = np.random.Generator(np.random.PCG64(parameters.seed))

    free_memories = list(range(parameters.n_memory_qubits))
    heapq.heapify(free_memories)
    busy_memories: list[tuple[float, int, int]] = []
    traced_attempt_ids: set[int] = set()
    trace: list[M2SimulationEvent] = []

    current_time = 0.0
    next_emitter_time = 0.0
    occupied_memories = 0
    occupancy_integral = 0.0
    occupancy_integral_compensation = 0.0
    occupancy_squared_integral = 0.0
    occupancy_squared_integral_compensation = 0.0
    occupancy_durations: dict[int, float] = {}
    peak_occupied_memories = 0
    attempts_launched = 0
    heralded_trials = 0
    successful_heralds = 0
    memory_releases = 0
    memory_wait_launches = 0
    emitter_memory_wait_time = 0.0
    attempt_id = 0

    def advance_time(target_time: float) -> None:
        nonlocal current_time
        nonlocal occupancy_integral
        nonlocal occupancy_integral_compensation
        nonlocal occupancy_squared_integral
        nonlocal occupancy_squared_integral_compensation
        nonlocal peak_occupied_memories
        if target_time < current_time:
            raise ArithmeticError("event time moved backwards")
        overlap = _interval_overlap(
            current_time,
            target_time,
            measurement_start,
            measurement_end,
        )
        if overlap > 0.0:
            area_increment = occupied_memories * overlap
            compensated_increment = area_increment - occupancy_integral_compensation
            updated_integral = occupancy_integral + compensated_increment
            occupancy_integral_compensation = (
                updated_integral - occupancy_integral - compensated_increment
            )
            occupancy_integral = updated_integral

            squared_increment = occupied_memories**2 * overlap
            compensated_squared_increment = (
                squared_increment - occupancy_squared_integral_compensation
            )
            updated_squared_integral = (
                occupancy_squared_integral + compensated_squared_increment
            )
            occupancy_squared_integral_compensation = (
                updated_squared_integral
                - occupancy_squared_integral
                - compensated_squared_increment
            )
            occupancy_squared_integral = updated_squared_integral
            occupancy_durations[occupied_memories] = (
                occupancy_durations.get(occupied_memories, 0.0) + overlap
            )
            peak_occupied_memories = max(
                peak_occupied_memories, occupied_memories
            )
        current_time = target_time

    while True:
        if free_memories:
            launch_time = next_emitter_time
        else:
            launch_time = max(next_emitter_time, busy_memories[0][0])

        release_processing_limit = min(launch_time, measurement_end)
        while (
            busy_memories
            and busy_memories[0][0] <= release_processing_limit
        ):
            release_time, memory_id, released_attempt_id = heapq.heappop(
                busy_memories
            )
            advance_time(release_time)
            occupied_memories -= 1
            heapq.heappush(free_memories, memory_id)
            if measurement_start <= release_time < measurement_end:
                memory_releases += 1
            if released_attempt_id in traced_attempt_ids:
                trace.append(
                    M2SimulationEvent(
                        time=release_time,
                        event_type=M2EventType.MEMORY_RELEASE,
                        attempt_id=released_attempt_id,
                        memory_id=memory_id,
                        occupied_memories=occupied_memories,
                        success=None,
                    )
                )

        if launch_time >= measurement_end:
            advance_time(measurement_end)
            break

        advance_time(launch_time)
        if not free_memories:
            raise ArithmeticError("no memory was available at the launch event")

        wait_duration = launch_time - next_emitter_time
        time_comparison_tolerance = 16.0 * math.ulp(
            max(launch_time, next_emitter_time, parameters.tau_e)
        )
        if wait_duration > time_comparison_tolerance:
            wait_overlap = _interval_overlap(
                next_emitter_time,
                launch_time,
                measurement_start,
                measurement_end,
            )
            emitter_memory_wait_time += wait_overlap
            if measurement_start <= launch_time < measurement_end:
                memory_wait_launches += 1

        memory_id = heapq.heappop(free_memories)
        occupied_memories += 1
        release_time = launch_time + tau_occ
        heapq.heappush(
            busy_memories,
            (release_time, memory_id, attempt_id),
        )
        success = bool(
            rng.random() < parameters.entanglement_success_probability
        )
        herald_time = launch_time + herald_delay

        if measurement_start <= launch_time < measurement_end:
            attempts_launched += 1
        if measurement_start <= herald_time < measurement_end:
            heralded_trials += 1
            successful_heralds += int(success)

        if attempt_id < parameters.trace_attempts:
            traced_attempt_ids.add(attempt_id)
            trace.append(
                M2SimulationEvent(
                    time=launch_time,
                    event_type=M2EventType.ATTEMPT_START,
                    attempt_id=attempt_id,
                    memory_id=memory_id,
                    occupied_memories=occupied_memories,
                    success=None,
                )
            )
            trace.append(
                M2SimulationEvent(
                    time=herald_time,
                    event_type=(
                        M2EventType.HERALD_SUCCESS
                        if success
                        else M2EventType.HERALD_FAILURE
                    ),
                    attempt_id=attempt_id,
                    memory_id=memory_id,
                    occupied_memories=None,
                    success=success,
                )
            )

        next_emitter_time = launch_time + parameters.tau_e
        attempt_id += 1

    mean_occupancy = occupancy_integral / parameters.measurement_duration
    occupancy_variance = max(
        0.0,
        occupancy_squared_integral / parameters.measurement_duration
        - mean_occupancy**2,
    )
    event_order = {
        M2EventType.MEMORY_RELEASE: 0,
        M2EventType.ATTEMPT_START: 1,
        M2EventType.HERALD_FAILURE: 2,
        M2EventType.HERALD_SUCCESS: 2,
    }
    trace.sort(
        key=lambda event: (
            event.time,
            event_order[event.event_type],
            event.attempt_id,
        )
    )
    runtime = time.perf_counter() - runtime_start
    occupancy_distribution = tuple(
        M2OccupancyTime(
            occupied_memories=level,
            duration=duration,
            fraction=duration / parameters.measurement_duration,
        )
        for level, duration in sorted(occupancy_durations.items())
        if duration > 0.0
    )

    return M2EventSimulationResult(
        seed=parameters.seed,
        warmup_duration=parameters.warmup_duration,
        measurement_duration=parameters.measurement_duration,
        tau_occ=tau_occ,
        total_attempts_simulated=attempt_id,
        attempts_launched=attempts_launched,
        heralded_trials=heralded_trials,
        successful_heralds=successful_heralds,
        memory_releases=memory_releases,
        memory_wait_launches=memory_wait_launches,
        emitter_memory_wait_time=emitter_memory_wait_time,
        attempt_rate=attempts_launched / parameters.measurement_duration,
        heralded_trial_rate=heralded_trials / parameters.measurement_duration,
        bell_pair_rate=successful_heralds / parameters.measurement_duration,
        empirical_success_probability=(
            successful_heralds / heralded_trials
            if heralded_trials > 0
            else None
        ),
        mean_occupied_memories=mean_occupancy,
        occupied_memories_std=math.sqrt(occupancy_variance),
        peak_occupied_memories=peak_occupied_memories,
        occupancy_time_distribution=occupancy_distribution,
        runtime_seconds=runtime,
        trace=tuple(trace),
    )
