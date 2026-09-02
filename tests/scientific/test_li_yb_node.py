import math
from decimal import Decimal, getcontext

import pytest

from quantum_telepathy.hardware.yb_node import (
    YbSystemLevelParameters,
    dark_count_false_positive_fraction,
    entanglement_success_probability,
    entanglement_trial_period,
    evaluate_yb_system_level,
    fiber_transmission,
    intrinsic_heg_rate,
    propagation_latency,
    tpi_success_probability,
)


getcontext().prec = 60


def _parameters(**overrides):
    values = {
        "internal_cooperativity": 20.0,
        "n_memory_qubits": 250,
        "n_channels": 1,
        "photon_emission_probability": 0.70,
        "photon_pulse_duration": 240e-9,
        "swap_time": 100e-9,
        "rotation_time": 100e-9,
        "measurement_time": 870e-9,
        "reset_time": 1e-6,
        "memory_lifetime": 7.9,
        "distance_km": 50.0,
        "attenuation_db_per_km": 0.25,
        "group_velocity_m_per_s": 2.1e8,
        "detector_efficiency": 0.9,
        "optics_efficiency": 0.8,
        "dark_count_rate": 10.0,
        "state_infidelity_upper_bound": 0.04,
        "measurement_infidelity": 0.002,
        "link_transmission_override": 0.06,
        "link_latency_override": 240e-6,
    }
    values.update(overrides)
    return YbSystemLevelParameters(**values)


def test_equations_54_to_61_match_independent_decimal_calculation():
    result = evaluate_yb_system_level(_parameters())

    p_e = Decimal("0.70")
    tau_p = Decimal("240e-9")
    tau_swap = Decimal("100e-9")
    tau_e = 2 * tau_p + tau_swap
    tpi_probability = p_e**2 / 2
    p_ent = tpi_probability * Decimal("0.06") * Decimal("0.9") ** 2 * Decimal(
        "0.8"
    ) ** 2
    tau_occ = (
        tau_e
        + Decimal("240e-6")
        + Decimal("100e-9")
        + Decimal("870e-9")
        + Decimal("1e-6")
    )
    gamma_heg = min(Decimal(1) / tau_e, Decimal(250) / tau_occ)
    epsilon = Decimal(1) - (
        Decimal(1) - Decimal(4) * Decimal("0.04") / Decimal(3)
    ) * (Decimal(1) - Decimal(2) * Decimal("0.002")) ** 2
    effective_state_error = Decimal("0.04") + Decimal(2) * (
        Decimal(1) - (-tau_occ / Decimal("7.9")).exp()
    )
    effective_epsilon = Decimal(1) - (
        Decimal(1) - Decimal(4) * effective_state_error / Decimal(3)
    ) * (Decimal(1) - Decimal(2) * Decimal("0.002")) ** 2

    assert result.tpi_success_probability == pytest.approx(
        float(tpi_probability), rel=1e-15
    )
    assert result.tau_e == pytest.approx(float(tau_e), abs=1e-20)
    assert result.intrinsic_heg_rate == pytest.approx(
        float(tpi_probability / tau_e), rel=1e-15
    )
    assert result.entanglement_success_probability == pytest.approx(
        float(p_ent), rel=1e-15
    )
    assert result.timing.tau_occ == pytest.approx(float(tau_occ), abs=1e-18)
    assert result.rate.r_heg == pytest.approx(
        float(p_ent * gamma_heg), rel=1e-15
    )
    assert result.dark_count_probability_per_attempt == pytest.approx(
        float(4 * tau_p * Decimal(10)), rel=1e-15
    )
    assert result.false_positive_fraction == pytest.approx(
        float(4 * tau_p * Decimal(10) / p_ent), rel=1e-15
    )
    assert result.combined_infidelity_upper_bound == pytest.approx(
        float(epsilon), rel=1e-15
    )
    assert result.memory_adjusted_state_infidelity_upper_bound == pytest.approx(
        float(effective_state_error), rel=1e-14
    )
    assert result.memory_adjusted_combined_infidelity_upper_bound == pytest.approx(
        float(effective_epsilon), rel=1e-14
    )


def test_distance_laws_are_retained_when_table_rounded_values_are_overridden():
    result = evaluate_yb_system_level(_parameters())
    decimal_exponent = -Decimal("0.25") * Decimal(50) / Decimal(10)
    expected_transmission = (Decimal(10).ln() * decimal_exponent).exp()

    assert result.link_transmission_source == "explicit_override"
    assert result.link_transmission == 0.06
    assert result.attenuation_law_transmission == pytest.approx(
        float(expected_transmission), rel=1e-15
    )
    assert result.link_latency_source == "explicit_override"
    assert result.tau_link == 240e-6
    assert result.propagation_latency == pytest.approx(50e3 / 2.1e8, rel=1e-15)


def test_unrounded_distance_model_is_used_without_overrides():
    result = evaluate_yb_system_level(
        _parameters(
            link_transmission_override=None,
            link_latency_override=None,
        )
    )

    assert result.link_transmission_source == "attenuation_law"
    assert result.link_transmission == result.attenuation_law_transmission
    assert result.link_latency_source == "distance_over_group_velocity"
    assert result.tau_link == result.propagation_latency
    assert result.rate.r_heg < evaluate_yb_system_level(_parameters()).rate.r_heg


def test_formula_helpers_cover_limit_cases_without_clipping():
    assert tpi_success_probability(0.0) == 0.0
    assert entanglement_trial_period(1.0, 0.0) == 2.0
    assert intrinsic_heg_rate(0.0, 1.0) == 0.0
    assert fiber_transmission(0.0, 100.0) == 1.0
    assert propagation_latency(0.0, 2e8) == 0.0
    assert entanglement_success_probability(1.0, 1.0, 1.0, 1.0) == 0.5
    assert dark_count_false_positive_fraction(1.0, 0.0, 0.0) == 0.0
    assert math.isinf(dark_count_false_positive_fraction(1.0, 1.0, 0.0))


def test_table3_case_is_memory_limited_and_final_rate_is_not_hardcoded():
    baseline = evaluate_yb_system_level(_parameters())
    more_memory = evaluate_yb_system_level(_parameters(n_memory_qubits=500))

    assert not baseline.timing.memory_depth_sufficient
    assert baseline.timing.minimum_memory_qubits == 419
    assert baseline.rate.r_heg == pytest.approx(7854.545454545455, rel=1e-15)
    assert more_memory.timing.memory_depth_sufficient
    assert more_memory.rate.r_heg > baseline.rate.r_heg


@pytest.mark.parametrize(
    ("overrides", "exception"),
    [
        ({"photon_emission_probability": 1.1}, ValueError),
        ({"photon_pulse_duration": 0.0}, ValueError),
        ({"n_memory_qubits": 0}, ValueError),
        ({"n_channels": True}, TypeError),
        ({"attenuation_db_per_km": -0.1}, ValueError),
        ({"link_transmission_override": math.nan}, ValueError),
        ({"link_latency_override": math.inf}, ValueError),
    ],
)
def test_yb_system_level_parameters_reject_invalid_values(overrides, exception):
    with pytest.raises(exception):
        _parameters(**overrides)
