import pytest

from quantum_telepathy.core.xor_game import (
    independent_bernoulli_distribution,
    uniform_distribution,
)
from quantum_telepathy.li2026.hft_waterfall import (
    StatisticsMethod,
    evaluate_hft_waterfall,
)
from quantum_telepathy.li2026.lctc import correlated_input_distribution
from quantum_telepathy.li2026.operational import CriterionStatus


TABLE3_EPSILON = 0.060972738493541345
TABLE3_RATE = 7854.545454545455


def _evaluate(**overrides):
    parameters = {
        "scenario_id": "test_scenario",
        "ding_p": 0.5,
        "ding_beta": 0.0,
        "input_distribution": uniform_distribution(),
        "beta1": 0.0,
        "beta2": 0.0,
        "epsilon": TABLE3_EPSILON,
        "alpha": 0.05,
        "t_env": 1.0,
        "r_heg": TABLE3_RATE,
        "tau_rot": 100e-9,
        "tau_meas": 870e-9,
        "t_loc": 10e-6,
        "t_comm": 240e-6,
    }
    parameters.update(overrides)
    return evaluate_hft_waterfall(**parameters)


def test_uniform_chsh_waterfall_uses_exact_binomial_and_passes():
    result = _evaluate()

    assert result.statistics_method is StatisticsMethod.EXACT_BINOMIAL
    assert result.ding_ideal_gap == pytest.approx(result.li_ideal_gap, abs=1e-12)
    assert result.model_transition_gap_change == pytest.approx(0.0, abs=1e-12)
    assert result.n_req == 65
    assert result.r_req == pytest.approx(65.0, abs=1e-12)
    assert result.overall_operational_quantum_advantage is CriterionStatus.PASS


def test_fractional_ding_case_uses_general_score_bound_without_model_drift():
    result = _evaluate(
        scenario_id="ding_representative_10s",
        ding_p=0.3,
        ding_beta=0.3,
        input_distribution=independent_bernoulli_distribution(0.3),
        beta1=0.3,
        beta2=0.3,
        t_env=10.0,
    )

    assert result.statistics_method is StatisticsMethod.GENERAL_SCORE_BOUND
    assert result.model_transition_gap_change == pytest.approx(0.0, abs=1e-12)
    assert result.n_req == 66133
    assert result.p_value_or_bound_at_n_req < result.alpha
    assert result.r_req == pytest.approx(6613.3, abs=1e-9)
    assert result.rate_criterion is CriterionStatus.PASS
    assert result.overall_operational_quantum_advantage is CriterionStatus.PASS


def test_statistics_interpretation_can_be_pinned_explicitly():
    result = _evaluate(
        ding_p=0.3,
        ding_beta=0.3,
        input_distribution=independent_bernoulli_distribution(0.3),
        beta1=0.3,
        beta2=0.3,
        statistics_method="general_score_bound",
        t_env=10.0,
    )

    assert result.statistics_method is StatisticsMethod.GENERAL_SCORE_BOUND


def test_short_stationary_window_exposes_rate_bottleneck():
    result = _evaluate(
        ding_p=0.3,
        ding_beta=0.3,
        input_distribution=independent_bernoulli_distribution(0.3),
        beta1=0.3,
        beta2=0.3,
        t_env=1.0,
    )

    assert result.theoretical_advantage is CriterionStatus.PASS
    assert result.fidelity_criterion is CriterionStatus.PASS
    assert result.statistical_certification is CriterionStatus.PASS
    assert result.rate_criterion is CriterionStatus.FAIL
    assert result.first_failed_criterion == "rate_criterion"
    assert result.dominant_bottleneck == "rate_criterion"
    assert result.overall_operational_quantum_advantage is CriterionStatus.FAIL


def test_correlated_asymmetric_generalization_is_supported():
    result = _evaluate(
        ding_p=0.5,
        ding_beta=0.05,
        input_distribution=correlated_input_distribution(0.4),
        beta1=0.05,
        beta2=0.1,
    )

    assert result.beta1 != result.beta2
    assert result.statistics_method is StatisticsMethod.GENERAL_SCORE_BOUND
    assert result.n_req == 1772
    assert result.overall_operational_quantum_advantage is CriterionStatus.PASS


def test_physical_infidelity_failure_stops_statistics_without_overclaiming():
    result = _evaluate(
        input_distribution=correlated_input_distribution(0.3),
        beta1=0.1,
        beta2=0.2,
    )

    assert result.theoretical_advantage is CriterionStatus.PASS
    assert result.fidelity_criterion is CriterionStatus.FAIL
    assert result.n_req is None
    assert result.statistical_certification is CriterionStatus.FAIL
    assert result.first_failed_criterion == "fidelity_criterion"
    assert result.overall_operational_quantum_advantage is CriterionStatus.FAIL


def test_decision_failure_is_separate_from_lctc_regime():
    result = _evaluate(t_loc=0.5e-6)

    assert result.latency_constrained_regime is CriterionStatus.PASS
    assert result.decision_criterion is CriterionStatus.FAIL
    assert result.first_failed_criterion == "decision_criterion"
    assert result.overall_operational_quantum_advantage is CriterionStatus.FAIL


def test_zero_ideal_gap_fails_before_operational_criteria():
    result = _evaluate(ding_beta=0.5, beta1=0.5, beta2=0.5)

    assert result.li_ideal_gap == pytest.approx(0.0, abs=1e-12)
    assert result.theoretical_advantage is CriterionStatus.FAIL
    assert result.first_failed_criterion == "theoretical_advantage"
    assert result.n_req is None


def test_waterfall_serialization_preserves_ordered_statuses():
    result = _evaluate()
    output = result.to_dict()
    stages = result.stages()

    assert output["statistics_method"] == "exact_binomial"
    assert output["overall_operational_quantum_advantage"] == "PASS"
    assert [stage["order"] for stage in stages] == list(range(1, 8))
    assert stages[-1]["status"] == "PASS"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("scenario_id", ""),
        ("epsilon", 1.1),
        ("alpha", 0.0),
        ("t_env", 0.0),
        ("r_heg", -1.0),
    ],
)
def test_waterfall_rejects_invalid_parameters(name, value):
    with pytest.raises(ValueError):
        _evaluate(**{name: value})
