import math

import numpy as np
import pytest

from quantum_telepathy.li2026.fidelity import (
    combined_infidelity,
    combined_infidelity_small_error_approx,
    measurement_visibility,
    noisy_gap,
    noisy_quantum_value,
    noisy_singlet_correlator,
    singlet_density_matrix,
    werner_state,
)


def test_combined_infidelity_uses_exact_li_expression():
    exact = combined_infidelity(epsilon_s=0.04, epsilon_meas=0.002)
    approx = combined_infidelity_small_error_approx(epsilon_s=0.04, epsilon_meas=0.002)

    assert exact == pytest.approx(0.06089152, abs=1e-12)
    assert exact < 0.061
    assert approx != pytest.approx(exact, abs=1e-8)


def test_noisy_quantum_value_and_gap_follow_li_equations():
    epsilon = 0.1
    classical_bias = 0.5
    quantum_bias = 0.75

    assert noisy_quantum_value(epsilon, quantum_bias) == pytest.approx(0.8375, abs=1e-12)
    assert noisy_gap(epsilon, classical_bias, quantum_bias) == pytest.approx(0.0875, abs=1e-12)


def test_werner_state_has_requested_singlet_infidelity():
    epsilon_s = 0.17
    singlet = singlet_density_matrix()
    state = werner_state(epsilon_s)

    assert np.trace(state).real == pytest.approx(1.0, abs=1e-12)
    assert np.trace(singlet @ state).real == pytest.approx(1.0 - epsilon_s, abs=1e-12)
    assert min(np.linalg.eigvalsh(state)) >= -1e-14


def test_density_matrix_correlator_recovers_exact_combined_infidelity():
    epsilon_s = 0.04
    epsilon_meas = 0.002
    alice = np.array([1.0, 2.0, -1.0]) / math.sqrt(6.0)
    bob = np.array([-2.0, 1.0, 2.0]) / 3.0
    epsilon = combined_infidelity(epsilon_s, epsilon_meas)

    direct = noisy_singlet_correlator(epsilon_s, epsilon_meas, alice, bob)
    expected = -(1.0 - epsilon) * float(np.dot(alice, bob))

    assert direct == pytest.approx(expected, abs=1e-12)
    assert measurement_visibility(epsilon_meas) == pytest.approx(0.996, abs=1e-12)


@pytest.mark.parametrize(
    ("alice", "bob"),
    [((1.0, 0.0), (1.0, 0.0, 0.0)), ((2.0, 0.0, 0.0), (1.0, 0.0, 0.0))],
)
def test_density_matrix_correlator_rejects_invalid_axes(alice, bob):
    with pytest.raises(ValueError):
        noisy_singlet_correlator(0.0, 0.0, alice, bob)


@pytest.mark.parametrize(
    ("epsilon_s", "epsilon_meas"),
    [(-0.1, 0.0), (0.0, -0.1), (1.1, 0.0), (0.0, 1.1)],
)
def test_combined_infidelity_rejects_invalid_probabilities(epsilon_s, epsilon_meas):
    with pytest.raises(ValueError):
        combined_infidelity(epsilon_s=epsilon_s, epsilon_meas=epsilon_meas)
