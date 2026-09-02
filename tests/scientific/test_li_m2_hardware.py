import math
from decimal import Decimal, getcontext

import pytest
from scipy.optimize import brentq

from quantum_telepathy.hardware.heg import (
    HEGRateParameters,
    evaluate_heg_rate,
    heralded_entanglement_generation_rate,
    meets_heg_rate_criterion,
)
from quantum_telepathy.hardware.memory_m0_m1_m2 import (
    M2TimingParameters,
    MemoryArchitecture,
    evaluate_m2_memory_fidelity,
    evaluate_m2_timing,
    heg_attempt_rate,
    memory_adjusted_state_infidelity,
    memory_depth_saturates,
    memory_lifetime_threshold,
    minimum_memory_qubits,
    occupancy_time,
)
from quantum_telepathy.li2026.operational import (
    CriterionStatus,
    evaluate_operational_advantage_from_error_components,
)


getcontext().prec = 60


def _timing_parameters(**overrides):
    values = {
        "tau_e": 580e-9,
        "tau_link": 240e-6,
        "tau_dec": 970e-9,
        "tau_res": 1e-6,
        "n_memory_qubits": 250,
    }
    values.update(overrides)
    return M2TimingParameters(**values)


def test_memory_architecture_identifiers_preserve_m0_m1_m2_taxonomy():
    assert tuple(model.value for model in MemoryArchitecture) == ("M0", "M1", "M2")


def test_m2_timing_matches_independent_decimal_equations_46_to_48():
    parameters = _timing_parameters()
    result = evaluate_m2_timing(parameters)
    tau_e = Decimal("580e-9")
    tau_occ = tau_e + Decimal("240e-6") + Decimal("970e-9") + Decimal("1e-6")
    expected_gamma = min(Decimal(1) / tau_e, Decimal(250) / tau_occ)

    assert result.architecture is MemoryArchitecture.M2
    assert result.tau_occ == pytest.approx(float(tau_occ), abs=1e-18)
    assert result.minimum_memory_qubits == 419
    assert not result.memory_depth_sufficient
    assert result.gamma_heg == pytest.approx(float(expected_gamma), rel=1e-15)


def test_memory_depth_and_attempt_rate_are_exact_at_saturation_boundary():
    tau_e = 0.25
    tau_occ = 1.0

    assert minimum_memory_qubits(tau_e, tau_occ) == 4
    assert not memory_depth_saturates(3, tau_e, tau_occ)
    assert memory_depth_saturates(4, tau_e, tau_occ)
    assert heg_attempt_rate(tau_e, 3, tau_occ) == 3.0
    assert heg_attempt_rate(tau_e, 4, tau_occ) == 4.0
    assert heg_attempt_rate(tau_e, 20, tau_occ) == 4.0


def test_occupancy_time_keeps_all_four_timescales_separate():
    assert occupancy_time(1.0, 2.0, 4.0, 8.0) == 15.0


def test_memory_infidelity_matches_independent_decimal_equation_49():
    epsilon_s = Decimal("0.04")
    tau_occ = Decimal("0.00024255")
    tau_mem = Decimal("7.9")
    expected = epsilon_s + Decimal(2) * (
        Decimal(1) - (-tau_occ / tau_mem).exp()
    )

    actual = memory_adjusted_state_infidelity(
        float(epsilon_s),
        float(tau_occ),
        float(tau_mem),
    )

    assert actual == pytest.approx(float(expected), rel=1e-14)


def test_infinite_memory_recovers_the_initial_state_infidelity():
    assert memory_adjusted_state_infidelity(0.04, 1.0, math.inf) == 0.04


def test_memory_lifetime_threshold_matches_independent_numerical_root():
    tau_occ = 242.55e-6
    epsilon_s = 0.04
    epsilon_meas = 0.002
    epsilon_threshold = 1.0 - 1.0 / math.sqrt(2.0)

    def independent_residual(tau_mem):
        effective_state_error = epsilon_s + 2.0 * (
            1.0 - math.exp(-tau_occ / tau_mem)
        )
        combined_error = 1.0 - (
            1.0 - 4.0 * effective_state_error / 3.0
        ) * (1.0 - 2.0 * epsilon_meas) ** 2
        return combined_error - epsilon_threshold

    numerical_root = brentq(independent_residual, tau_occ / 100.0, 1e3)
    analytical = memory_lifetime_threshold(
        tau_occ,
        epsilon_threshold,
        epsilon_meas,
        epsilon_s,
    )

    assert analytical == pytest.approx(numerical_root, rel=1e-11)


def test_memory_lifetime_criterion_is_strict_at_equation_50_boundary():
    tau_occ = 242.55e-6
    epsilon_threshold = 1.0 - 1.0 / math.sqrt(2.0)
    threshold = memory_lifetime_threshold(
        tau_occ,
        epsilon_threshold,
        0.002,
        0.04,
    )

    at_boundary = evaluate_m2_memory_fidelity(
        tau_occ=tau_occ,
        tau_mem=threshold,
        epsilon_s=0.04,
        epsilon_meas=0.002,
        epsilon_threshold=epsilon_threshold,
    )
    above_boundary = evaluate_m2_memory_fidelity(
        tau_occ=tau_occ,
        tau_mem=math.nextafter(threshold, math.inf),
        epsilon_s=0.04,
        epsilon_meas=0.002,
        epsilon_threshold=epsilon_threshold,
    )

    assert not at_boundary.memory_lifetime_criterion
    assert not at_boundary.fidelity_criterion
    assert above_boundary.memory_lifetime_criterion
    assert above_boundary.fidelity_criterion


def test_no_finite_memory_lifetime_when_base_error_reaches_threshold():
    base_error = 1.0 - (1.0 - 4.0 * 0.04 / 3.0) * (1.0 - 2.0 * 0.002) ** 2

    assert math.isinf(memory_lifetime_threshold(1.0, base_error, 0.002, 0.04))


def test_out_of_domain_memory_error_is_reported_without_clipping():
    result = evaluate_m2_memory_fidelity(
        tau_occ=1.0,
        tau_mem=0.01,
        epsilon_s=0.04,
        epsilon_meas=0.002,
        epsilon_threshold=0.3,
    )

    assert result.epsilon_s_effective > 1.0
    assert not result.model_domain_valid
    assert result.epsilon is None
    assert not result.fidelity_criterion


def test_heg_rate_matches_independent_decimal_equation_52():
    gamma_heg = Decimal("1030587.847308103")
    p_ent = Decimal("0.0077")
    expected = Decimal(2) * p_ent * gamma_heg

    actual = heralded_entanglement_generation_rate(
        float(gamma_heg),
        float(p_ent),
        n_channels=2,
    )

    assert actual == pytest.approx(float(expected), rel=1e-15)


def test_heg_rate_is_linear_in_channels_and_zero_at_zero_success_probability():
    one_channel = evaluate_heg_rate(HEGRateParameters(1e6, 0.01, 1))
    four_channels = evaluate_heg_rate(HEGRateParameters(1e6, 0.01, 4))

    assert four_channels.r_heg == 4.0 * one_channel.r_heg
    assert heralded_entanglement_generation_rate(1e6, 0.0, 4) == 0.0


def test_heg_rate_criterion_is_strict_at_equation_53_boundary():
    assert not meets_heg_rate_criterion(2380.0, 2380.0)
    assert meets_heg_rate_criterion(math.nextafter(2380.0, math.inf), 2380.0)


def test_m2_models_reject_nonfinite_derived_rates_and_depths():
    with pytest.raises(ValueError, match="memory depth"):
        minimum_memory_qubits(1e-308, 1e308)
    with pytest.raises(ValueError, match="R_HEG"):
        heralded_entanglement_generation_rate(1e308, 1.0, 2)


def test_m2_outputs_feed_the_operational_status_without_hardcoded_final_rate():
    timing = evaluate_m2_timing(_timing_parameters())
    memory = evaluate_m2_memory_fidelity(
        tau_occ=timing.tau_occ,
        tau_mem=7.9,
        epsilon_s=0.04,
        epsilon_meas=0.002,
        epsilon_threshold=1.0 - 1.0 / math.sqrt(2.0),
    )
    rate = evaluate_heg_rate(
        HEGRateParameters(
            gamma_heg=timing.gamma_heg,
            entanglement_success_probability=0.0077,
            n_channels=1,
        )
    )
    assert memory.epsilon is not None
    status = evaluate_operational_advantage_from_error_components(
        classical_bias=0.5,
        quantum_bias=1.0 / math.sqrt(2.0),
        epsilon_s=memory.epsilon_s_effective,
        epsilon_meas=memory.epsilon_meas,
        alpha=0.001,
        t_env=0.1,
        r_heg=rate.r_heg,
        tau_rot=100e-9,
        tau_meas=870e-9,
        t_loc=10e-6,
        t_comm=240e-6,
    )

    expected_rate = float(
        Decimal(250)
        / (
            Decimal("580e-9")
            + Decimal("240e-6")
            + Decimal("970e-9")
            + Decimal("1e-6")
        )
        * Decimal("0.0077")
    )
    assert rate.r_heg == pytest.approx(expected_rate, rel=1e-15)
    assert memory.memory_lifetime_criterion
    assert memory.fidelity_criterion
    assert status.rate_criterion is CriterionStatus.PASS
    assert status.fidelity_criterion is CriterionStatus.PASS
    assert status.overall_operational_quantum_advantage is CriterionStatus.PASS


@pytest.mark.parametrize(
    ("factory", "arguments", "exception"),
    [
        (M2TimingParameters, (-1.0, 0.0, 0.0, 0.0, 1), ValueError),
        (M2TimingParameters, (1.0, math.inf, 0.0, 0.0, 1), ValueError),
        (M2TimingParameters, (1.0, 0.0, 0.0, 0.0, 0), ValueError),
        (M2TimingParameters, (1.0, 0.0, 0.0, 0.0, 1.5), TypeError),
        (HEGRateParameters, (0.0, 0.1, 1), ValueError),
        (HEGRateParameters, (1.0, 1.1, 1), ValueError),
        (HEGRateParameters, (1.0, 0.1, True), TypeError),
    ],
)
def test_m2_models_reject_invalid_parameters(factory, arguments, exception):
    with pytest.raises(exception):
        factory(*arguments)
