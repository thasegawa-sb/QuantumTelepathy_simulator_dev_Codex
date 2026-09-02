import math

import pytest

from quantum_telepathy.li2026.operational import (
    CriterionStatus,
    DecisionCriterion,
    evaluate_operational_advantage,
    evaluate_operational_advantage_from_error_components,
)


CHSH_CLASSICAL_BIAS = 0.5
CHSH_QUANTUM_BIAS = 1.0 / math.sqrt(2.0)


def _passing_status(**overrides):
    parameters = {
        "classical_bias": CHSH_CLASSICAL_BIAS,
        "quantum_bias": CHSH_QUANTUM_BIAS,
        "epsilon_s": 0.04,
        "epsilon_meas": 0.002,
        "alpha": 0.001,
        "t_env": 0.1,
        "r_heg": 7900.0,
        "tau_rot": 100e-9,
        "tau_meas": 870e-9,
        "t_loc": 10e-6,
        "t_comm": 240e-6,
    }
    parameters.update(overrides)
    return evaluate_operational_advantage_from_error_components(**parameters)


def test_decision_criterion_implements_li_equations_44_and_45():
    criterion = DecisionCriterion(tau_rot=100e-9, tau_meas=870e-9, t_loc=1e-6)

    assert criterion.tau_dec == pytest.approx(970e-9, abs=1e-18)
    assert criterion.status is CriterionStatus.PASS


def test_decision_criterion_is_strict_at_the_local_window_boundary():
    criterion = DecisionCriterion(tau_rot=0.25, tau_meas=0.75, t_loc=1.0)

    assert criterion.tau_dec == 1.0
    assert criterion.status is CriterionStatus.FAIL


def test_chsh_operational_scenario_passes_all_required_criteria():
    result = _passing_status()

    assert result.latency_constrained_regime is CriterionStatus.PASS
    assert result.theoretical_advantage is CriterionStatus.PASS
    assert result.fidelity_criterion is CriterionStatus.PASS
    assert result.statistical_certification is CriterionStatus.PASS
    assert result.rate_criterion is CriterionStatus.PASS
    assert result.decision_criterion is CriterionStatus.PASS
    assert result.overall_operational_quantum_advantage is CriterionStatus.PASS
    assert result.epsilon == pytest.approx(0.06089152, abs=1e-12)
    assert result.epsilon_threshold == pytest.approx(
        1.0 - 1.0 / math.sqrt(2.0), abs=1e-12
    )
    assert result.n_req == 238
    assert result.expected_wins_at_n_req == 199
    assert result.p_value_at_n_req == pytest.approx(
        0.0009172732139019824,
        rel=1e-12,
    )
    assert result.p_value_at_n_req < result.alpha
    assert result.r_req == pytest.approx(2380.0, abs=1e-12)
    assert result.r_heg > result.r_req


def test_fidelity_threshold_equality_fails_without_claiming_certification():
    threshold = 1.0 - 1.0 / math.sqrt(2.0)
    result = evaluate_operational_advantage(
        classical_bias=CHSH_CLASSICAL_BIAS,
        quantum_bias=CHSH_QUANTUM_BIAS,
        epsilon=threshold,
        alpha=0.05,
        t_env=1.0,
        r_heg=1e9,
        tau_rot=0.1,
        tau_meas=0.1,
        t_loc=0.5,
        t_comm=1.0,
    )

    assert result.theoretical_advantage is CriterionStatus.PASS
    assert result.fidelity_criterion is CriterionStatus.FAIL
    assert result.statistical_certification is CriterionStatus.FAIL
    assert result.rate_criterion is CriterionStatus.FAIL
    assert result.n_req is None
    assert result.r_req is None
    assert result.overall_operational_quantum_advantage is CriterionStatus.FAIL


def test_rate_criterion_is_strict_at_required_rate_equality():
    reference = _passing_status()
    result = _passing_status(r_heg=reference.r_req)

    assert result.statistical_certification is CriterionStatus.PASS
    assert result.r_heg == result.r_req
    assert result.rate_criterion is CriterionStatus.FAIL
    assert result.overall_operational_quantum_advantage is CriterionStatus.FAIL


def test_latency_regime_and_decision_deadline_are_independent():
    no_lctc_regime = _passing_status(t_loc=240e-6, t_comm=240e-6)
    missed_decision = _passing_status(tau_meas=20e-6, t_loc=10e-6, t_env=10.0)

    assert no_lctc_regime.decision_criterion is CriterionStatus.PASS
    assert no_lctc_regime.latency_constrained_regime is CriterionStatus.FAIL
    assert no_lctc_regime.overall_operational_quantum_advantage is CriterionStatus.FAIL
    assert missed_decision.decision_criterion is CriterionStatus.FAIL
    assert missed_decision.latency_constrained_regime is CriterionStatus.PASS
    assert missed_decision.overall_operational_quantum_advantage is CriterionStatus.FAIL


def test_positive_theoretical_gap_alone_never_produces_overall_pass():
    result = evaluate_operational_advantage(
        classical_bias=CHSH_CLASSICAL_BIAS,
        quantum_bias=CHSH_QUANTUM_BIAS,
        epsilon=0.0,
        alpha=0.05,
        t_env=1.0,
        r_heg=0.0,
        tau_rot=1.0,
        tau_meas=1.0,
        t_loc=1.0,
        t_comm=2.0,
    )

    assert result.theoretical_advantage is CriterionStatus.PASS
    assert result.fidelity_criterion is CriterionStatus.PASS
    assert result.statistical_certification is CriterionStatus.PASS
    assert result.rate_criterion is CriterionStatus.FAIL
    assert result.decision_criterion is CriterionStatus.FAIL
    assert result.overall_operational_quantum_advantage is CriterionStatus.FAIL


def test_nonadvantageous_game_returns_traceable_fail_not_statistics_exception():
    result = evaluate_operational_advantage(
        classical_bias=0.5,
        quantum_bias=0.5,
        epsilon=0.0,
        alpha=0.05,
        t_env=1.0,
        r_heg=1e9,
        tau_rot=0.1,
        tau_meas=0.1,
        t_loc=0.5,
        t_comm=1.0,
    )

    assert result.theoretical_advantage is CriterionStatus.FAIL
    assert result.fidelity_criterion is CriterionStatus.FAIL
    assert result.statistical_certification is CriterionStatus.FAIL
    assert result.overall_operational_quantum_advantage is CriterionStatus.FAIL


def test_standard_output_serializes_statuses_as_pass_fail_strings():
    output = _passing_status().to_dict()

    assert output["theoretical_advantage"] == "PASS"
    assert output["fidelity_criterion"] == "PASS"
    assert output["rate_criterion"] == "PASS"
    assert output["decision_criterion"] == "PASS"
    assert output["statistical_certification"] == "PASS"
    assert output["overall_operational_quantum_advantage"] == "PASS"
    assert output["tau_dec"] == pytest.approx(970e-9, abs=1e-18)


@pytest.mark.parametrize(
    ("factory", "overrides"),
    [
        (DecisionCriterion, {"tau_rot": -1.0, "tau_meas": 0.0, "t_loc": 1.0}),
        (DecisionCriterion, {"tau_rot": 0.0, "tau_meas": math.inf, "t_loc": 1.0}),
        (DecisionCriterion, {"tau_rot": 0.0, "tau_meas": 0.0, "t_loc": math.nan}),
    ],
)
def test_decision_criterion_rejects_invalid_durations(factory, overrides):
    with pytest.raises(ValueError):
        factory(**overrides)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("epsilon", -0.1),
        ("alpha", 0.0),
        ("t_env", 0.0),
        ("r_heg", -1.0),
        ("t_comm", math.inf),
    ],
)
def test_operational_status_rejects_invalid_parameters(name, value):
    parameters = {
        "classical_bias": CHSH_CLASSICAL_BIAS,
        "quantum_bias": CHSH_QUANTUM_BIAS,
        "epsilon": 0.0,
        "alpha": 0.05,
        "t_env": 1.0,
        "r_heg": 100.0,
        "tau_rot": 0.1,
        "tau_meas": 0.1,
        "t_loc": 0.5,
        "t_comm": 1.0,
    }
    parameters[name] = value

    with pytest.raises(ValueError):
        evaluate_operational_advantage(**parameters)
