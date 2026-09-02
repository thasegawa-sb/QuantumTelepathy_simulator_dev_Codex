import itertools
import math

import numpy as np
import pytest

from quantum_telepathy.li2026.multiparty import (
    canonical_paper_strategy_bias,
    combined_ghz_infidelity,
    enumerated_three_party_classical_optimum,
    evaluate_three_party_operational_advantage,
    ghz_state_vector,
    majority,
    noisy_ghz_correlator,
    noisy_ghz_state,
    noisy_three_party_quantum_value,
    three_party_fidelity_threshold,
    three_party_game_coefficients,
    three_party_input_distribution,
    three_party_majority_utility,
    three_party_values,
)
from quantum_telepathy.li2026.operational import CriterionStatus
from quantum_telepathy.multiparty.xor import (
    binary_input_tuples,
    deterministic_classical_bias,
    independent_bernoulli_distribution,
    optimize_ghz_equatorial_bias,
    symmetric_ghz_equatorial_bias,
    validate_binary_input_distribution,
)


def test_binary_input_helpers_cover_complete_normalized_distribution():
    inputs = binary_input_tuples(3)
    distribution = independent_bernoulli_distribution(3, 0.3)

    assert len(inputs) == 8
    assert set(distribution) == set(inputs)
    assert sum(distribution.values()) == pytest.approx(1.0, abs=1e-15)
    assert validate_binary_input_distribution(distribution) == 3


@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        ((0, 0, 0), 0),
        ((1, 0, 0), 0),
        ((1, 1, 0), 1),
        ((1, 1, 1), 1),
    ],
)
def test_majority_matches_li_equations_63_and_b6(inputs, expected):
    assert majority(inputs) == expected


def test_soft_majority_utility_matches_equations_65_and_b12():
    utility = three_party_majority_utility(0.2)

    assert (utility(0, (0, 0, 0)), utility(1, (0, 0, 0))) == (1.0, 0.0)
    assert (utility(0, (1, 0, 0)), utility(1, (1, 0, 0))) == (0.8, 0.2)
    assert (utility(0, (1, 1, 0)), utility(1, (1, 1, 0))) == (0.2, 0.8)
    assert (utility(0, (1, 1, 1)), utility(1, (1, 1, 1))) == (0.0, 1.0)


def test_uniform_hard_majority_recovers_chsh_equivalent_values():
    values = three_party_values(0.5, 0.0)

    assert values.classical_bias == pytest.approx(0.5, abs=1e-12)
    assert values.quantum_bias == pytest.approx(1.0 / math.sqrt(2.0), abs=1e-12)
    assert values.classical_value == pytest.approx(0.75, abs=1e-12)
    assert values.quantum_value == pytest.approx(
        (1.0 + 1.0 / math.sqrt(2.0)) / 2.0, abs=1e-12
    )
    assert values.gap == pytest.approx((math.sqrt(2.0) - 1.0) / 4.0, abs=1e-12)
    assert canonical_paper_strategy_bias() == pytest.approx(
        1.0 / math.sqrt(2.0), abs=1e-12
    )


@pytest.mark.parametrize(
    ("probability_one", "beta"),
    [(0.1, 0.1), (0.3, 0.0), (0.3, 0.2), (0.5, 0.0), (0.7, 0.4), (0.9, 0.49)],
)
def test_classical_bias_matches_independent_64_strategy_utility_enumeration(
    probability_one, beta
):
    coefficients = three_party_game_coefficients(probability_one, beta)
    bias_result = deterministic_classical_bias(coefficients)
    utility_result = enumerated_three_party_classical_optimum(probability_one, beta)

    assert bias_result.strategy_count == 64
    assert utility_result.strategy_count == 64
    assert (1.0 + bias_result.bias) / 2.0 == pytest.approx(
        utility_result.value, abs=1e-12
    )


@pytest.mark.parametrize(
    ("probability_one", "beta"),
    [(0.1, 0.1), (0.3, 0.0), (0.3, 0.2), (0.5, 0.0), (0.7, 0.4), (0.9, 0.49)],
)
def test_symmetric_quantum_bias_matches_independent_three_phase_optimization(
    probability_one, beta
):
    coefficients = three_party_game_coefficients(probability_one, beta)
    production = three_party_values(probability_one, beta)
    independent = optimize_ghz_equatorial_bias(coefficients, seed=2026)

    assert production.quantum_bias == pytest.approx(
        independent.bias, rel=0.0, abs=2e-9
    )


@pytest.mark.parametrize("probability_one", [0.0, 0.1, 0.5, 0.9, 1.0])
def test_beta_half_and_deterministic_input_limits_have_zero_gap(probability_one):
    assert three_party_values(probability_one, 0.5).gap == pytest.approx(
        0.0, abs=1e-12
    )
    if probability_one in (0.0, 1.0):
        for beta in (0.0, 0.2, 0.8, 1.0):
            assert three_party_values(probability_one, beta).gap == pytest.approx(
                0.0, abs=1e-12
            )


def test_ghz_state_error_model_has_expected_trace_spectrum_and_fidelity():
    epsilon = 0.14
    state = noisy_ghz_state(epsilon)
    ghz = ghz_state_vector()
    eigenvalues = np.linalg.eigvalsh(state)

    assert np.trace(state) == pytest.approx(1.0, abs=1e-12)
    assert eigenvalues.min() >= -1e-14
    assert float(np.vdot(ghz, state @ ghz).real) == pytest.approx(
        1.0 - epsilon, abs=1e-12
    )


@pytest.mark.parametrize(
    ("epsilon_ghz", "epsilon_meas", "angles"),
    [
        (0.0, 0.0, (0.2, -0.4, 0.7)),
        (0.05, 0.01, (0.1, 0.3, -0.2)),
        (0.2, 0.08, (-0.7, 0.2, 1.1)),
    ],
)
def test_direct_density_matrix_correlator_matches_equations_b17_b18(
    epsilon_ghz, epsilon_meas, angles
):
    epsilon = combined_ghz_infidelity(epsilon_ghz, epsilon_meas)
    expected = (1.0 - epsilon) * math.cos(sum(angles))

    assert noisy_ghz_correlator(
        epsilon_ghz, epsilon_meas, angles
    ) == pytest.approx(expected, abs=1e-12)


def test_canonical_multiparty_fidelity_threshold_matches_equation_b22():
    classical = 0.75
    quantum = (1.0 + 1.0 / math.sqrt(2.0)) / 2.0
    threshold = three_party_fidelity_threshold(classical, quantum)

    assert threshold == pytest.approx(1.0 - 1.0 / math.sqrt(2.0), abs=1e-12)
    assert noisy_three_party_quantum_value(threshold, quantum) == pytest.approx(
        classical, abs=1e-12
    )


def _passing_operational_status(**overrides):
    parameters = {
        "probability_one": 0.5,
        "beta": 0.0,
        "epsilon_ghz": 0.05,
        "epsilon_meas": 0.01,
        "alpha": 0.05,
        "t_env": 0.1,
        "r_ghz": 1e6,
        "tau_rot": 100e-9,
        "tau_meas": 870e-9,
        "t_loc": 10e-6,
        "t_comm": 240e-6,
    }
    parameters.update(overrides)
    return evaluate_three_party_operational_advantage(**parameters)


def test_three_party_operational_status_uses_exact_binomial_path_and_passes():
    result = _passing_operational_status()

    assert result.combined_infidelity == pytest.approx(0.1125904, abs=1e-12)
    assert result.statistics_method == "exact_binomial"
    assert result.n_req == 107
    assert result.r_req == pytest.approx(1070.0, abs=1e-12)
    assert result.overall_operational_quantum_advantage is CriterionStatus.PASS


def test_three_party_operational_boundaries_fail_without_overclaiming():
    rate_reference = _passing_operational_status()
    rate_failure = _passing_operational_status(r_ghz=rate_reference.r_req)
    decision_failure = _passing_operational_status(t_loc=970e-9)
    no_advantage = _passing_operational_status(beta=0.5)

    assert rate_failure.rate_criterion is CriterionStatus.FAIL
    assert decision_failure.decision_criterion is CriterionStatus.FAIL
    assert no_advantage.theoretical_advantage is CriterionStatus.FAIL
    assert no_advantage.n_req is None
    assert all(
        result.overall_operational_quantum_advantage is CriterionStatus.FAIL
        for result in (rate_failure, decision_failure, no_advantage)
    )


def test_three_party_fidelity_threshold_equality_fails_strictly():
    threshold = 1.0 - 1.0 / math.sqrt(2.0)
    state_error = 7.0 * threshold / 8.0
    result = _passing_operational_status(
        epsilon_ghz=state_error,
        epsilon_meas=0.0,
    )

    assert result.combined_infidelity == pytest.approx(threshold, abs=1e-15)
    assert result.fidelity_criterion is CriterionStatus.FAIL
    assert result.statistical_certification is CriterionStatus.FAIL
    assert result.overall_operational_quantum_advantage is CriterionStatus.FAIL


def test_three_party_input_distribution_matches_iid_formula():
    probability = 0.3
    distribution = three_party_input_distribution(probability)

    for inputs in itertools.product((0, 1), repeat=3):
        weight = sum(inputs)
        assert distribution[inputs] == pytest.approx(
            probability**weight * (1.0 - probability) ** (3 - weight),
            abs=1e-15,
        )


def test_symmetric_optimizer_rejects_nonexchangeable_coefficients():
    coefficients = three_party_game_coefficients(0.5, 0.0)
    coefficients[(0, 0, 1)] += 0.01

    with pytest.raises(ValueError, match="permutation-symmetric"):
        symmetric_ghz_equatorial_bias(coefficients)


@pytest.mark.parametrize(
    ("function", "arguments"),
    [
        (binary_input_tuples, (0,)),
        (independent_bernoulli_distribution, (3, -0.1)),
        (majority, ((0, 1),)),
        (three_party_majority_utility, (1.1,)),
        (combined_ghz_infidelity, (-0.1, 0.0)),
        (noisy_ghz_correlator, (0.0, 0.0, (0.0, 0.0))),
        (three_party_fidelity_threshold, (0.75, 0.5)),
    ],
)
def test_multiparty_functions_reject_invalid_parameters(function, arguments):
    with pytest.raises(ValueError):
        function(*arguments)
