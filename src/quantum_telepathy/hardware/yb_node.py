"""System-level neutral-atom network model for Li et al. Eqs. 54-61.

The model consumes experimentally meaningful device and network parameters.
It does not attempt to reproduce the microscopic cavity simulations in
Appendix C. All durations use seconds, distances use kilometres, and rates use
inverse seconds.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from quantum_telepathy.hardware.heg import (
    HEGRateParameters,
    HEGRateResult,
    evaluate_heg_rate,
)
from quantum_telepathy.hardware.memory_m0_m1_m2 import (
    M2TimingParameters,
    M2TimingResult,
    evaluate_m2_timing,
    memory_adjusted_state_infidelity,
)
from quantum_telepathy.li2026.fidelity import combined_infidelity


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


def tpi_success_probability(photon_emission_probability: float) -> float:
    """Return the intrinsic TPI success probability ``p_e^2 / 2``."""

    emission_probability = _probability(
        "photon_emission_probability", photon_emission_probability
    )
    return emission_probability**2 / 2.0


def entanglement_trial_period(
    photon_pulse_duration: float,
    swap_time: float,
) -> float:
    """Return Li Eq. 55, ``tau_e = 2 tau_p + tau_swap``."""

    pulse_duration = _finite_positive(
        "photon_pulse_duration", photon_pulse_duration
    )
    state_swap_time = _finite_nonnegative("swap_time", swap_time)
    result = 2.0 * pulse_duration + state_swap_time
    if not math.isfinite(result):
        raise ValueError("tau_e must be finite")
    return result


def intrinsic_heg_rate(
    photon_emission_probability: float,
    tau_e: float,
) -> float:
    """Return Li Eq. 54, ``R0 = (p_e^2 / 2) / tau_e``."""

    trial_period = _finite_positive("tau_e", tau_e)
    return tpi_success_probability(photon_emission_probability) / trial_period


def fiber_transmission(
    distance_km: float,
    attenuation_db_per_km: float,
) -> float:
    """Return ``eta_att(L) = 10^(-alpha_att L / 10)`` from Li Eq. 56."""

    distance = _finite_nonnegative("distance_km", distance_km)
    attenuation = _finite_nonnegative(
        "attenuation_db_per_km", attenuation_db_per_km
    )
    return 10.0 ** (-attenuation * distance / 10.0)


def propagation_latency(
    distance_km: float,
    group_velocity_m_per_s: float,
) -> float:
    """Return the one-way link latency ``L / v_g`` used in Table III."""

    distance = _finite_nonnegative("distance_km", distance_km)
    group_velocity = _finite_positive(
        "group_velocity_m_per_s", group_velocity_m_per_s
    )
    return distance * 1000.0 / group_velocity


def entanglement_success_probability(
    photon_emission_probability: float,
    link_transmission: float,
    detector_efficiency: float,
    optics_efficiency: float,
) -> float:
    """Return Li Eq. 56 for a time-bin two-photon-interference trial."""

    transmission = _probability("link_transmission", link_transmission)
    detector = _probability("detector_efficiency", detector_efficiency)
    optics = _probability("optics_efficiency", optics_efficiency)
    return (
        tpi_success_probability(photon_emission_probability)
        * transmission
        * detector**2
        * optics**2
    )


def dark_count_false_positive_fraction(
    photon_pulse_duration: float,
    dark_count_rate: float,
    entanglement_probability: float,
) -> float:
    """Return Li Eq. 58, ``p_false = 4 tau_p D / p_ent(L)``.

    The expression estimates the false-positive fraction among heralds. It is
    left unclipped so callers can detect parameter regimes outside its
    probability interpretation.
    """

    pulse_duration = _finite_positive(
        "photon_pulse_duration", photon_pulse_duration
    )
    count_rate = _finite_nonnegative("dark_count_rate", dark_count_rate)
    success_probability = _probability(
        "entanglement_probability", entanglement_probability
    )
    if success_probability == 0.0:
        return math.inf if count_rate > 0.0 else 0.0
    return 4.0 * pulse_duration * count_rate / success_probability


@dataclass(frozen=True)
class YbSystemLevelParameters:
    """Device and network inputs for the Li Table III system-level model."""

    internal_cooperativity: float
    n_memory_qubits: int
    n_channels: int
    photon_emission_probability: float
    photon_pulse_duration: float
    swap_time: float
    rotation_time: float
    measurement_time: float
    reset_time: float
    memory_lifetime: float
    distance_km: float
    attenuation_db_per_km: float
    group_velocity_m_per_s: float
    detector_efficiency: float
    optics_efficiency: float
    dark_count_rate: float
    state_infidelity_upper_bound: float
    measurement_infidelity: float
    link_transmission_override: float | None = None
    link_latency_override: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "internal_cooperativity",
            _finite_positive("internal_cooperativity", self.internal_cooperativity),
        )
        if isinstance(self.n_memory_qubits, bool) or not isinstance(
            self.n_memory_qubits, int
        ):
            raise TypeError("n_memory_qubits must be an integer")
        if self.n_memory_qubits <= 0:
            raise ValueError("n_memory_qubits must be positive")
        if isinstance(self.n_channels, bool) or not isinstance(self.n_channels, int):
            raise TypeError("n_channels must be an integer")
        if self.n_channels <= 0:
            raise ValueError("n_channels must be positive")

        probability_fields = (
            "photon_emission_probability",
            "detector_efficiency",
            "optics_efficiency",
            "state_infidelity_upper_bound",
            "measurement_infidelity",
        )
        for name in probability_fields:
            object.__setattr__(self, name, _probability(name, getattr(self, name)))

        positive_fields = (
            "photon_pulse_duration",
            "memory_lifetime",
            "group_velocity_m_per_s",
        )
        for name in positive_fields:
            object.__setattr__(self, name, _finite_positive(name, getattr(self, name)))

        nonnegative_fields = (
            "swap_time",
            "rotation_time",
            "measurement_time",
            "reset_time",
            "distance_km",
            "attenuation_db_per_km",
            "dark_count_rate",
        )
        for name in nonnegative_fields:
            object.__setattr__(
                self, name, _finite_nonnegative(name, getattr(self, name))
            )

        if self.link_transmission_override is not None:
            object.__setattr__(
                self,
                "link_transmission_override",
                _probability(
                    "link_transmission_override", self.link_transmission_override
                ),
            )
        if self.link_latency_override is not None:
            object.__setattr__(
                self,
                "link_latency_override",
                _finite_nonnegative(
                    "link_latency_override", self.link_latency_override
                ),
            )


@dataclass(frozen=True)
class YbSystemLevelResult:
    """Traceable outputs of Li Eqs. 44 and 54-61 plus M2 Eqs. 46-52."""

    tpi_success_probability: float
    tau_e: float
    intrinsic_heg_rate: float
    attenuation_law_transmission: float
    link_transmission: float
    link_transmission_source: str
    propagation_latency: float
    tau_link: float
    link_latency_source: str
    tau_dec: float
    entanglement_success_probability: float
    dark_count_probability_per_attempt: float
    false_positive_fraction: float
    false_positive_model_domain_valid: bool
    timing: M2TimingResult
    rate: HEGRateResult
    state_infidelity_upper_bound: float
    measurement_infidelity: float
    combined_infidelity_upper_bound: float
    memory_adjusted_state_infidelity_upper_bound: float
    memory_adjusted_combined_infidelity_upper_bound: float | None


def evaluate_yb_system_level(
    parameters: YbSystemLevelParameters,
) -> YbSystemLevelResult:
    """Evaluate the platform-specific quantities without hardcoding outcomes."""

    tau_e = entanglement_trial_period(
        parameters.photon_pulse_duration,
        parameters.swap_time,
    )
    attenuation_law = fiber_transmission(
        parameters.distance_km,
        parameters.attenuation_db_per_km,
    )
    if parameters.link_transmission_override is None:
        transmission = attenuation_law
        transmission_source = "attenuation_law"
    else:
        transmission = parameters.link_transmission_override
        transmission_source = "explicit_override"

    calculated_latency = propagation_latency(
        parameters.distance_km,
        parameters.group_velocity_m_per_s,
    )
    if parameters.link_latency_override is None:
        tau_link = calculated_latency
        latency_source = "distance_over_group_velocity"
    else:
        tau_link = parameters.link_latency_override
        latency_source = "explicit_override"

    tau_dec = parameters.rotation_time + parameters.measurement_time
    timing = evaluate_m2_timing(
        M2TimingParameters(
            tau_e=tau_e,
            tau_link=tau_link,
            tau_dec=tau_dec,
            tau_res=parameters.reset_time,
            n_memory_qubits=parameters.n_memory_qubits,
        )
    )
    success_probability = entanglement_success_probability(
        parameters.photon_emission_probability,
        transmission,
        parameters.detector_efficiency,
        parameters.optics_efficiency,
    )
    rate = evaluate_heg_rate(
        HEGRateParameters(
            gamma_heg=timing.gamma_heg,
            entanglement_success_probability=success_probability,
            n_channels=parameters.n_channels,
        )
    )
    false_positive_fraction = dark_count_false_positive_fraction(
        parameters.photon_pulse_duration,
        parameters.dark_count_rate,
        success_probability,
    )
    combined_error = combined_infidelity(
        parameters.state_infidelity_upper_bound,
        parameters.measurement_infidelity,
    )
    effective_state_error = memory_adjusted_state_infidelity(
        parameters.state_infidelity_upper_bound,
        timing.tau_occ,
        parameters.memory_lifetime,
    )
    effective_combined_error = (
        combined_infidelity(effective_state_error, parameters.measurement_infidelity)
        if 0.0 <= effective_state_error <= 1.0
        else None
    )

    return YbSystemLevelResult(
        tpi_success_probability=tpi_success_probability(
            parameters.photon_emission_probability
        ),
        tau_e=tau_e,
        intrinsic_heg_rate=intrinsic_heg_rate(
            parameters.photon_emission_probability,
            tau_e,
        ),
        attenuation_law_transmission=attenuation_law,
        link_transmission=transmission,
        link_transmission_source=transmission_source,
        propagation_latency=calculated_latency,
        tau_link=tau_link,
        link_latency_source=latency_source,
        tau_dec=tau_dec,
        entanglement_success_probability=success_probability,
        dark_count_probability_per_attempt=(
            4.0 * parameters.photon_pulse_duration * parameters.dark_count_rate
        ),
        false_positive_fraction=false_positive_fraction,
        false_positive_model_domain_valid=0.0 <= false_positive_fraction <= 1.0,
        timing=timing,
        rate=rate,
        state_infidelity_upper_bound=parameters.state_infidelity_upper_bound,
        measurement_infidelity=parameters.measurement_infidelity,
        combined_infidelity_upper_bound=combined_error,
        memory_adjusted_state_infidelity_upper_bound=effective_state_error,
        memory_adjusted_combined_infidelity_upper_bound=effective_combined_error,
    )
