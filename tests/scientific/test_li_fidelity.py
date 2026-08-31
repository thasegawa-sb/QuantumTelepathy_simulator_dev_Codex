import pytest

from quantum_telepathy.li2026.fidelity import (
    combined_infidelity,
    combined_infidelity_small_error_approx,
    noisy_gap,
    noisy_quantum_value,
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


@pytest.mark.parametrize(
    ("epsilon_s", "epsilon_meas"),
    [(-0.1, 0.0), (0.0, -0.1), (1.1, 0.0), (0.0, 1.1)],
)
def test_combined_infidelity_rejects_invalid_probabilities(epsilon_s, epsilon_meas):
    with pytest.raises(ValueError):
        combined_infidelity(epsilon_s=epsilon_s, epsilon_meas=epsilon_meas)
