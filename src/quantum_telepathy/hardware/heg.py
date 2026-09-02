"""Platform-independent heralded entanglement generation rate formulas."""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Integral


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


@dataclass(frozen=True)
class HEGRateParameters:
    """Inputs to Li Eq. 52 after the M2 attempt rate has been evaluated."""

    gamma_heg: float
    entanglement_success_probability: float
    n_channels: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gamma_heg",
            _finite_positive("gamma_heg", self.gamma_heg),
        )
        object.__setattr__(
            self,
            "entanglement_success_probability",
            _probability(
                "entanglement_success_probability",
                self.entanglement_success_probability,
            ),
        )
        object.__setattr__(
            self,
            "n_channels",
            _positive_integer("n_channels", self.n_channels),
        )


@dataclass(frozen=True)
class HEGRateResult:
    """Decomposed HEG throughput quantities for Li Eqs. 52-53."""

    gamma_heg: float
    entanglement_success_probability: float
    n_channels: int
    r_heg: float


def heralded_entanglement_generation_rate(
    gamma_heg: float,
    entanglement_success_probability: float,
    n_channels: int = 1,
) -> float:
    """Return Li Eq. 52, ``R_HEG = N_ch p_ent Gamma_HEG``."""

    attempt_rate = _finite_positive("gamma_heg", gamma_heg)
    success_probability = _probability(
        "entanglement_success_probability",
        entanglement_success_probability,
    )
    channel_count = _positive_integer("n_channels", n_channels)
    result = channel_count * success_probability * attempt_rate
    if not math.isfinite(result):
        raise ValueError("R_HEG is not finite")
    return result


def meets_heg_rate_criterion(r_heg: float, r_req: float) -> bool:
    """Return True exactly when the strict Li Eq. 53 criterion holds."""

    entanglement_rate = _finite_nonnegative("r_heg", r_heg)
    required_rate = _finite_nonnegative("r_req", r_req)
    return entanglement_rate > required_rate


def evaluate_heg_rate(parameters: HEGRateParameters) -> HEGRateResult:
    """Evaluate the system-level HEG rate while preserving its inputs."""

    return HEGRateResult(
        gamma_heg=parameters.gamma_heg,
        entanglement_success_probability=parameters.entanglement_success_probability,
        n_channels=parameters.n_channels,
        r_heg=heralded_entanglement_generation_rate(
            parameters.gamma_heg,
            parameters.entanglement_success_probability,
            parameters.n_channels,
        ),
    )
