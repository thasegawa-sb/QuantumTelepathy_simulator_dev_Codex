import numpy as np
import pytest

from quantum_telepathy.core.xor_game import independent_bernoulli_distribution
from quantum_telepathy.ding_jiang.hft import hedging_utility, ideal_hedging_values
from quantum_telepathy.ding_jiang.loss import (
    find_loss_threshold,
    lossy_bell_operator,
    lossy_expected_utility,
    optimize_lossy_value,
    projective_measurement,
    schmidt_coefficients,
)

INPUT_DISTRIBUTION = independent_bernoulli_distribution(0.3)
UTILITY = hedging_utility(0.3)
PAPER_FALLBACK = ((0, 0), (1, 1))
PAPER_ROUNDED_STATE = (0.0401, -0.902, -0.428, -0.0401)


@pytest.fixture(scope="module")
def representative_optimization():
    return optimize_lossy_value(
        INPUT_DISTRIBUTION,
        UTILITY,
        (0.95, 0.95),
        grid_size=20,
        local_starts=2,
    )


@pytest.fixture(scope="module")
def representative_threshold():
    return find_loss_threshold(
        INPUT_DISTRIBUTION,
        UTILITY,
        classical_value=0.79,
        efficiency_tolerance=2e-5,
        advantage_tolerance=1e-9,
        grid_size=12,
        local_starts=1,
    )


def test_projective_measurement_is_complete_and_orthogonal():
    projector_zero, projector_one = projective_measurement(-0.590)

    assert np.allclose(projector_zero + projector_one, np.eye(2), atol=1e-12)
    assert np.allclose(projector_zero @ projector_one, np.zeros((2, 2)), atol=1e-12)
    assert np.allclose(projector_zero @ projector_zero, projector_zero, atol=1e-12)


def test_eq_a11_direct_mixture_matches_eq_a12_bell_operator():
    state = np.asarray(PAPER_ROUNDED_STATE, dtype=float)
    state /= np.linalg.norm(state)
    operator = lossy_bell_operator(
        INPUT_DISTRIBUTION,
        UTILITY,
        (0.87, 0.93),
        (-0.590, -0.590),
        PAPER_FALLBACK,
    )
    operator_value = float(state @ operator @ state)
    direct_value = lossy_expected_utility(
        INPUT_DISTRIBUTION,
        UTILITY,
        (0.87, 0.93),
        (-0.590, -0.590),
        PAPER_FALLBACK,
        state,
    )

    assert direct_value == pytest.approx(operator_value, abs=1e-12)


def test_paper_rounded_strategy_reproduces_reported_lossy_value():
    value = lossy_expected_utility(
        INPUT_DISTRIBUTION,
        UTILITY,
        (0.95, 0.95),
        (-0.590, -0.590),
        PAPER_FALLBACK,
        PAPER_ROUNDED_STATE,
    )

    assert value == pytest.approx(0.792, abs=1e-3)


def test_representative_lossy_optimum_matches_paper(representative_optimization):
    result = representative_optimization

    assert result.value == pytest.approx(0.792, abs=5e-4)
    assert result.fallback_strategy in (PAPER_FALLBACK, ((1, 1), (0, 0)))
    assert schmidt_coefficients(result.state) == pytest.approx((0.903, 0.429), abs=5e-4)
    assert lossy_expected_utility(
        INPUT_DISTRIBUTION,
        UTILITY,
        result.efficiencies,
        result.angles,
        result.fallback_strategy,
        result.state,
    ) == pytest.approx(result.value, abs=1e-12)


def test_loss_threshold_matches_paper(representative_threshold):
    assert representative_threshold.threshold == pytest.approx(0.941, abs=5e-4)
    assert representative_threshold.upper_bound - representative_threshold.lower_bound <= 2e-5


def test_loss_threshold_eta_one_value_matches_ideal_game(representative_threshold):
    eta_one = next(
        evaluation
        for evaluation in representative_threshold.evaluations
        if evaluation.efficiency == 1.0
    )
    ideal = ideal_hedging_values(0.3, 0.3)

    assert eta_one.quantum_value == pytest.approx(ideal.quantum_value, abs=1e-9)


def test_both_lost_reduces_to_fallback_deterministic_value():
    value = lossy_expected_utility(
        INPUT_DISTRIBUTION,
        UTILITY,
        (0.0, 0.0),
        (0.21, -0.37),
        ((1, 1), (0, 1)),
        PAPER_ROUNDED_STATE,
    )

    assert value == pytest.approx(0.79, abs=1e-12)
