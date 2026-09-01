import math
from itertools import product

import numpy as np
import pytest

from quantum_telepathy.core.xor_game import independent_bernoulli_distribution
from quantum_telepathy.ding_jiang.fig3 import independent_classical_value
from quantum_telepathy.ding_jiang.hft import hedging_utility, ideal_hedging_values
from quantum_telepathy.ding_jiang.loss import (
    lossy_expected_utility,
    optimize_lossy_value,
    projective_measurement,
)
from quantum_telepathy.ding_jiang.loss_sdp import (
    evaluate_correlator_functional,
    find_npa_threshold_lower_bound,
    lossy_correlator_functional,
    lossy_npa_upper_bound,
)


def _observable(angle):
    zero, one = projective_measurement(angle)
    return zero - one


def _moments(angles, state):
    vector = np.asarray(state, dtype=float)
    vector /= np.linalg.norm(vector)
    identity = np.eye(2)
    alice = (_observable(0.0), _observable(angles[0]))
    bob = (_observable(0.0), _observable(angles[1]))
    alice_marginals = tuple(
        float(vector @ np.kron(observable, identity) @ vector)
        for observable in alice
    )
    bob_marginals = tuple(
        float(vector @ np.kron(identity, observable) @ vector)
        for observable in bob
    )
    correlators = tuple(
        tuple(
            float(vector @ np.kron(alice[x], bob[y]) @ vector)
            for y in range(2)
        )
        for x in range(2)
    )
    return alice_marginals, bob_marginals, correlators


def test_correlator_functional_matches_direct_eq_a11():
    distribution = independent_bernoulli_distribution(0.37)
    utility = hedging_utility(0.23)
    efficiencies = (0.81, 0.93)
    fallback = ((0, 1), (1, 0))
    angles = (0.41, -0.67)
    state = (0.19, -0.73, 0.61, 0.24)
    functional = lossy_correlator_functional(
        distribution,
        utility,
        efficiencies,
        fallback,
    )
    alice, bob, correlators = _moments(angles, state)

    moment_value = evaluate_correlator_functional(
        functional,
        alice,
        bob,
        correlators,
    )
    direct_value = lossy_expected_utility(
        distribution,
        utility,
        efficiencies,
        angles,
        fallback,
        state,
    )

    assert moment_value == pytest.approx(direct_value, abs=1e-12)


def test_q1ab_upper_bound_recovers_no_loss_chsh_value():
    distribution = independent_bernoulli_distribution(0.5)
    utility = hedging_utility(0.0)
    expected = (1.0 + 1.0 / math.sqrt(2.0)) / 2.0

    result = lossy_npa_upper_bound(distribution, utility, (1.0, 1.0))

    assert result.raw_upper_bound == pytest.approx(expected, abs=1e-7)
    assert result.upper_bound >= expected - 1e-10
    assert len(result.evaluations) == 16
    assert all(evaluation.solver_status == "optimal" for evaluation in result.evaluations)


@pytest.mark.parametrize(("p", "beta"), [(0.3, 0.3), (0.5, 0.4), (0.7, 0.2)])
def test_q1ab_guarded_bound_covers_independent_no_loss_xor_solution(p, beta):
    distribution = independent_bernoulli_distribution(p)
    utility = hedging_utility(beta)
    expected = ideal_hedging_values(p, beta).quantum_value

    result = lossy_npa_upper_bound(
        distribution,
        utility,
        (1.0, 1.0),
        solver_tolerance=1e-8,
    )

    assert result.upper_bound >= expected
    assert result.upper_bound - expected <= 1.1e-7


def test_q1ab_bound_is_above_explicit_lossy_strategy():
    distribution = independent_bernoulli_distribution(0.3)
    utility = hedging_utility(0.3)
    lower = optimize_lossy_value(
        distribution,
        utility,
        (0.95, 0.95),
        grid_size=12,
        local_starts=1,
    )
    upper = lossy_npa_upper_bound(distribution, utility, (0.95, 0.95))

    assert upper.upper_bound >= lower.value - 1e-10
    assert upper.upper_bound - lower.value <= 5e-4


def test_zero_efficiency_upper_bound_is_classical_fallback_value():
    distribution = independent_bernoulli_distribution(0.3)
    utility = hedging_utility(0.3)
    classical, _ = independent_classical_value(0.3, 0.3)

    result = lossy_npa_upper_bound(distribution, utility, (0.0, 0.0))

    assert result.raw_upper_bound == pytest.approx(classical, abs=1e-8)
    assert result.upper_bound == pytest.approx(classical + 1e-7, abs=2e-8)


@pytest.mark.parametrize(
    ("p", "beta", "efficiency"),
    [(0.5, 0.0, 0.9), (0.3, 0.3, 0.95), (0.7, 0.4, 0.97)],
)
def test_npa_upper_bound_dominates_configured_lower_bounds(p, beta, efficiency):
    distribution = independent_bernoulli_distribution(p)
    utility = hedging_utility(beta)
    lower = optimize_lossy_value(
        distribution,
        utility,
        (efficiency, efficiency),
        grid_size=8,
        local_starts=1,
    )
    upper = lossy_npa_upper_bound(
        distribution,
        utility,
        (efficiency, efficiency),
    )

    assert upper.upper_bound >= lower.value - 1e-9


def test_npa_threshold_lower_bound_brackets_representative_paper_value():
    distribution = independent_bernoulli_distribution(0.3)
    utility = hedging_utility(0.3)
    classical, _ = independent_classical_value(0.3, 0.3)

    result = find_npa_threshold_lower_bound(
        distribution,
        utility,
        classical,
        efficiency_tolerance=5e-4,
    )

    assert result.threshold_lower_bound <= 0.941
    assert 0.941 - result.threshold_lower_bound <= 0.02
    assert result.transition_upper_bound - result.threshold_lower_bound <= 5e-4
    assert all(
        status in ("optimal", "optimal_inaccurate")
        for evaluation in result.evaluations
        for status in evaluation.solver_statuses
    )
    efficiencies = [evaluation.efficiency for evaluation in result.evaluations]
    assert len(efficiencies) == len(set(efficiencies))
