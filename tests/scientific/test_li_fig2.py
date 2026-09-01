import math

import pytest
from scipy.optimize import differential_evolution

from quantum_telepathy.core.xor_game import independent_bernoulli_distribution
from quantum_telepathy.ding_jiang.hft import ideal_hedging_values
from quantum_telepathy.li2026.fidelity import fidelity_threshold, noisy_gap
from quantum_telepathy.li2026.lctc import (
    correlated_input_distribution,
    enumerated_classical_optimum,
    generalized_lctc_matrix,
    generalized_lctc_values,
)


def _direct_angle_quantum_bias(matrix):
    """Independent planar measurement-angle optimization for selected points."""

    def negative_bias(angles):
        alice = angles[:2]
        bob = (0.0, angles[2])
        return -sum(
            matrix[x][y] * math.cos(alice[x] - bob[y])
            for x in range(2)
            for y in range(2)
        )

    result = differential_evolution(
        negative_bias,
        bounds=((-math.pi, math.pi),) * 3,
        seed=260407451,
        tol=1e-11,
        polish=True,
    )
    assert result.success
    return -float(result.fun)


@pytest.mark.parametrize(
    ("p11", "expected"),
    [
        (0.0, ((1.0, 0.0), (0.0, 0.0))),
        (0.2, ((0.6, 0.1), (0.1, 0.2))),
        (0.5, ((0.0, 0.25), (0.25, 0.5))),
    ],
)
def test_figure2b_correlated_distribution(p11, expected):
    distribution = correlated_input_distribution(p11)

    for x in range(2):
        for y in range(2):
            assert distribution[x][y] == pytest.approx(expected[x][y], abs=1e-12)
    assert sum(sum(row) for row in distribution) == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("p11", [-0.01, 0.5001])
def test_figure2b_correlated_distribution_rejects_invalid_parameter(p11):
    with pytest.raises(ValueError):
        correlated_input_distribution(p11)


@pytest.mark.parametrize(
    ("distribution", "beta1", "beta2"),
    [
        (independent_bernoulli_distribution(0.5), 0.0, 0.0),
        (independent_bernoulli_distribution(0.31), 0.17, 0.17),
        (correlated_input_distribution(0.23), 0.19, 0.07),
        (correlated_input_distribution(0.47), 0.35, 0.12),
    ],
)
def test_li_classical_value_matches_independent_strategy_enumeration(
    distribution, beta1, beta2
):
    values = generalized_lctc_values(distribution, beta1, beta2)
    oracle = enumerated_classical_optimum(distribution, beta1, beta2)

    assert oracle.strategy_count == 16
    assert values.classical_value == pytest.approx(oracle.value, abs=1e-12)


@pytest.mark.parametrize(
    ("distribution", "beta1", "beta2"),
    [
        (independent_bernoulli_distribution(0.5), 0.0, 0.0),
        (independent_bernoulli_distribution(0.31), 0.17, 0.17),
        (correlated_input_distribution(0.23), 0.19, 0.07),
    ],
)
def test_li_quantum_bias_matches_independent_measurement_angle_optimization(
    distribution, beta1, beta2
):
    values = generalized_lctc_values(distribution, beta1, beta2)
    oracle = _direct_angle_quantum_bias(
        generalized_lctc_matrix(distribution, beta1, beta2)
    )

    assert values.quantum_bias == pytest.approx(oracle, abs=1e-9)


@pytest.mark.parametrize("p", [0.0, 0.17, 0.5, 0.83, 1.0])
@pytest.mark.parametrize("beta", [0.0, 0.13, 0.5, 0.87, 1.0])
def test_figure2a_matches_ding_ideal_values_under_output_relabeling(p, beta):
    li = generalized_lctc_values(independent_bernoulli_distribution(p), beta, beta)
    ding = ideal_hedging_values(p, beta)

    assert li.classical_value == pytest.approx(ding.classical_value, abs=1e-12)
    assert li.quantum_value == pytest.approx(ding.quantum_value, abs=1e-12)
    assert li.gap == pytest.approx(ding.gap, abs=1e-12)


def test_figure2c_chsh_limits_and_threshold():
    values = generalized_lctc_values(independent_bernoulli_distribution(0.5), 0.0, 0.0)
    expected_gap = (math.sqrt(2.0) - 1.0) / 4.0
    expected_threshold = 1.0 - 1.0 / math.sqrt(2.0)

    assert values.gap == pytest.approx(expected_gap, abs=1e-12)
    assert fidelity_threshold(values.classical_bias, values.quantum_bias) == pytest.approx(
        expected_threshold, abs=1e-12
    )
    assert noisy_gap(
        expected_threshold, values.classical_bias, values.quantum_bias
    ) == pytest.approx(0.0, abs=1e-12)
