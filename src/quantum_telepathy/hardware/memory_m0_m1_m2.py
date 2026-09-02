"""Memory architecture taxonomy and Li et al. M2 analytical formulas.

M0 and M1 remain implemented by the paper-specific Ding-Jiang loss and memory
modules.  This module adds M2 without reinterpreting either validated model.
All durations use seconds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from numbers import Integral

from quantum_telepathy.li2026.fidelity import combined_infidelity


class MemoryArchitecture(str, Enum):
    """Stable identifiers for the project's M0/M1/M2 memory taxonomy."""

    M0 = "M0"
    M1 = "M1"
    M2 = "M2"


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


def _positive_or_infinite(name: str, value: float) -> float:
    result = float(value)
    if math.isnan(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive")
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


@dataclass(frozen=True)
class M2TimingParameters:
    """Timing and memory-depth parameters for Li Eqs. 46-48."""

    tau_e: float
    tau_link: float
    tau_dec: float
    tau_res: float
    n_memory_qubits: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "tau_e", _finite_positive("tau_e", self.tau_e))
        object.__setattr__(
            self,
            "tau_link",
            _finite_nonnegative("tau_link", self.tau_link),
        )
        object.__setattr__(
            self,
            "tau_dec",
            _finite_nonnegative("tau_dec", self.tau_dec),
        )
        object.__setattr__(
            self,
            "tau_res",
            _finite_nonnegative("tau_res", self.tau_res),
        )
        object.__setattr__(
            self,
            "n_memory_qubits",
            _positive_integer("n_memory_qubits", self.n_memory_qubits),
        )


@dataclass(frozen=True)
class M2TimingResult:
    """Traceable M2 occupancy, depth, and HEG-attempt quantities."""

    architecture: MemoryArchitecture
    tau_e: float
    tau_link: float
    tau_dec: float
    tau_res: float
    tau_occ: float
    n_memory_qubits: int
    minimum_memory_qubits: int
    memory_depth_sufficient: bool
    gamma_heg: float


def occupancy_time(
    tau_e: float,
    tau_link: float,
    tau_dec: float,
    tau_res: float,
) -> float:
    """Return Li Eq. 46, ``tau_occ = tau_e + tau_link + tau_dec + tau_res``."""

    attempt_duration = _finite_positive("tau_e", tau_e)
    link_latency = _finite_nonnegative("tau_link", tau_link)
    decision_latency = _finite_nonnegative("tau_dec", tau_dec)
    reset_duration = _finite_nonnegative("tau_res", tau_res)
    result = attempt_duration + link_latency + decision_latency + reset_duration
    if not math.isfinite(result):
        raise ValueError("tau_occ must be finite")
    return result


def minimum_memory_qubits(tau_e: float, tau_occ: float) -> int:
    """Return the minimum integer ``N_a`` satisfying Li Eq. 47."""

    attempt_duration = _finite_positive("tau_e", tau_e)
    occupancy = _finite_nonnegative("tau_occ", tau_occ)
    ratio = occupancy / attempt_duration
    if not math.isfinite(ratio):
        raise ValueError("required memory depth is not finite")
    return int(math.ceil(math.nextafter(ratio, -math.inf)))


def memory_depth_saturates(
    n_memory_qubits: int,
    tau_e: float,
    tau_occ: float,
) -> bool:
    """Return whether ``N_a tau_e >= tau_occ`` in Li Eq. 47."""

    memory_count = _positive_integer("n_memory_qubits", n_memory_qubits)
    attempt_duration = _finite_positive("tau_e", tau_e)
    occupancy = _finite_nonnegative("tau_occ", tau_occ)
    return memory_count * attempt_duration >= occupancy


def heg_attempt_rate(
    tau_e: float,
    n_memory_qubits: int,
    tau_occ: float,
) -> float:
    """Return Li Eq. 48, ``Gamma_HEG = min(1/tau_e, N_a/tau_occ)``."""

    attempt_duration = _finite_positive("tau_e", tau_e)
    memory_count = _positive_integer("n_memory_qubits", n_memory_qubits)
    occupancy = _finite_positive("tau_occ", tau_occ)
    channel_limited_rate = 1.0 / attempt_duration
    try:
        memory_limited_rate = memory_count / occupancy
    except OverflowError:
        memory_limited_rate = math.inf
    result = min(channel_limited_rate, memory_limited_rate)
    if not math.isfinite(result):
        raise ValueError("Gamma_HEG is not finite")
    return result


def evaluate_m2_timing(parameters: M2TimingParameters) -> M2TimingResult:
    """Evaluate Li Eqs. 46-48 for one time-multiplexed memory bank."""

    tau_occ = occupancy_time(
        parameters.tau_e,
        parameters.tau_link,
        parameters.tau_dec,
        parameters.tau_res,
    )
    required_memories = minimum_memory_qubits(parameters.tau_e, tau_occ)
    return M2TimingResult(
        architecture=MemoryArchitecture.M2,
        tau_e=parameters.tau_e,
        tau_link=parameters.tau_link,
        tau_dec=parameters.tau_dec,
        tau_res=parameters.tau_res,
        tau_occ=tau_occ,
        n_memory_qubits=parameters.n_memory_qubits,
        minimum_memory_qubits=required_memories,
        memory_depth_sufficient=memory_depth_saturates(
            parameters.n_memory_qubits,
            parameters.tau_e,
            tau_occ,
        ),
        gamma_heg=heg_attempt_rate(
            parameters.tau_e,
            parameters.n_memory_qubits,
            tau_occ,
        ),
    )


def memory_adjusted_state_infidelity(
    epsilon_s: float,
    tau_occ: float,
    tau_mem: float,
) -> float:
    """Return Li Eq. 49 using a stable exponential evaluation."""

    initial_error = _probability("epsilon_s", epsilon_s)
    occupancy = _finite_nonnegative("tau_occ", tau_occ)
    memory_lifetime = _positive_or_infinite("tau_mem", tau_mem)
    if math.isinf(memory_lifetime):
        return initial_error
    decoherence_error = -2.0 * math.expm1(-occupancy / memory_lifetime)
    return initial_error + decoherence_error


def memory_lifetime_threshold(
    tau_occ: float,
    epsilon_threshold: float,
    epsilon_meas: float,
    epsilon_s: float,
) -> float:
    """Return Li Eq. 51, or infinity when Eq. 50 has no finite solution."""

    occupancy = _finite_nonnegative("tau_occ", tau_occ)
    threshold = _probability("epsilon_threshold", epsilon_threshold)
    measurement_error = _probability("epsilon_meas", epsilon_meas)
    state_error = _probability("epsilon_s", epsilon_s)

    if combined_infidelity(state_error, measurement_error) >= threshold:
        return math.inf
    if occupancy == 0.0:
        return 0.0

    visibility_squared = (1.0 - 2.0 * measurement_error) ** 2
    if visibility_squared == 0.0:
        return math.inf
    error_margin = (
        1.0
        - 4.0 * state_error / 3.0
        - (1.0 - threshold) / visibility_squared
    )
    if error_margin <= 0.0:
        return math.inf

    log_argument = math.log1p(-3.0 * error_margin / 8.0)
    if log_argument >= 0.0:
        return math.inf
    return -occupancy / log_argument


@dataclass(frozen=True)
class M2MemoryFidelityResult:
    """Memory-adjusted state and combined-error diagnostics for Li Eqs. 49-51."""

    tau_occ: float
    tau_mem: float
    tau_mem_threshold: float
    epsilon_s: float
    epsilon_s_effective: float
    epsilon_meas: float
    epsilon: float | None
    epsilon_threshold: float
    model_domain_valid: bool
    memory_lifetime_criterion: bool
    fidelity_criterion: bool


def evaluate_m2_memory_fidelity(
    *,
    tau_occ: float,
    tau_mem: float,
    epsilon_s: float,
    epsilon_meas: float,
    epsilon_threshold: float,
) -> M2MemoryFidelityResult:
    """Evaluate memory decoherence and the strict Li Eq. 50 requirement."""

    occupancy = _finite_nonnegative("tau_occ", tau_occ)
    memory_lifetime = _positive_or_infinite("tau_mem", tau_mem)
    state_error = _probability("epsilon_s", epsilon_s)
    measurement_error = _probability("epsilon_meas", epsilon_meas)
    threshold = _probability("epsilon_threshold", epsilon_threshold)
    effective_state_error = memory_adjusted_state_infidelity(
        state_error,
        occupancy,
        memory_lifetime,
    )
    lifetime_threshold = memory_lifetime_threshold(
        occupancy,
        threshold,
        measurement_error,
        state_error,
    )
    state_domain_valid = 0.0 <= effective_state_error <= 1.0
    raw_combined_error = (
        combined_infidelity(effective_state_error, measurement_error)
        if state_domain_valid
        else None
    )
    domain_valid = (
        raw_combined_error is not None and 0.0 <= raw_combined_error <= 1.0
    )
    effective_combined_error = raw_combined_error if domain_valid else None
    lifetime_passes = memory_lifetime > lifetime_threshold
    fidelity_passes = (
        domain_valid
        and lifetime_passes
        and effective_combined_error is not None
        and effective_combined_error < threshold
    )
    return M2MemoryFidelityResult(
        tau_occ=occupancy,
        tau_mem=memory_lifetime,
        tau_mem_threshold=lifetime_threshold,
        epsilon_s=state_error,
        epsilon_s_effective=effective_state_error,
        epsilon_meas=measurement_error,
        epsilon=effective_combined_error,
        epsilon_threshold=threshold,
        model_domain_valid=domain_valid,
        memory_lifetime_criterion=lifetime_passes,
        fidelity_criterion=fidelity_passes,
    )
