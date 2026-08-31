import math

import pytest

from quantum_telepathy.core.xor_game import (
    chsh_matrix,
    gap,
    independent_bernoulli_distribution,
    quantum_value,
    uniform_distribution,
    xor_game_matrix,
)
from quantum_telepathy.ding_jiang.hft import (
    biased_chsh_values,
    hedging_matrix,
    hedging_utility,
    ideal_hedging_values,
)
from quantum_telepathy.li2026.lctc import (
    check_latency_constraint,
    generalized_lctc_matrix,
    generalized_lctc_utility,
)


def assert_matrix2x2_close(actual, expected, abs=1e-12):
    for x in range(2):
        for y in range(2):
            assert actual[x][y] == pytest.approx(expected[x][y], abs=abs)


def test_li_generalized_utility_reduces_to_chsh_matrix():
    matrix = generalized_lctc_matrix(uniform_distribution(), beta1=0.0, beta2=0.0)

    assert_matrix2x2_close(matrix, chsh_matrix())


def test_li_generalized_utility_supports_asymmetric_betas():
    utility = generalized_lctc_utility(beta1=0.2, beta2=0.3)

    assert utility[0][0] == pytest.approx((1.0, 0.0), abs=1e-12)
    assert utility[0][1] == pytest.approx((0.8, 0.2), abs=1e-12)
    assert utility[1][0] == pytest.approx((0.7, 0.3), abs=1e-12)
    assert utility[1][1] == pytest.approx((0.0, 1.0), abs=1e-12)

    pxy = ((0.1, 0.2), (0.3, 0.4))
    matrix = generalized_lctc_matrix(pxy, beta1=0.2, beta2=0.3)
    assert_matrix2x2_close(matrix, ((0.1, 0.12), (0.12, -0.4)))


def test_ding_hedging_utility_is_anti_chsh_at_beta_zero():
    ding_matrix = xor_game_matrix(uniform_distribution(), hedging_utility(beta=0.0))

    assert_matrix2x2_close(
        ding_matrix,
        tuple(tuple(-value for value in row) for row in chsh_matrix()),
    )
    assert quantum_value(ding_matrix) == pytest.approx(
        (1.0 + 1.0 / math.sqrt(2.0)) / 2.0,
        abs=1e-12,
    )


@pytest.mark.parametrize("p", [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
def test_ding_biased_chsh_theorem_matches_xor_core_at_beta_zero(p):
    theorem = biased_chsh_values(p)
    computed = ideal_hedging_values(p, beta=0.0)

    assert computed.classical_value == pytest.approx(theorem.classical_value, abs=1e-10)
    assert computed.quantum_value == pytest.approx(theorem.quantum_value, abs=1e-10)
    assert computed.gap == pytest.approx(theorem.gap, abs=1e-10)


def test_ding_beta_symmetry_for_ideal_gap():
    p = 0.37
    beta = 0.2

    assert gap(hedging_matrix(p, beta)) == pytest.approx(
        gap(hedging_matrix(p, 1.0 - beta)),
        abs=1e-12,
    )


def test_lctc_latency_constraint_is_strict():
    assert check_latency_constraint(t_loc=1.0, t_comm=2.0)
    assert not check_latency_constraint(t_loc=1.0, t_comm=1.0)
    assert not check_latency_constraint(t_loc=2.0, t_comm=1.0)


def test_independent_bernoulli_distribution_is_ordered_by_x_y():
    pxy = independent_bernoulli_distribution(0.3)

    assert_matrix2x2_close(pxy, ((0.49, 0.21), (0.21, 0.09)))
