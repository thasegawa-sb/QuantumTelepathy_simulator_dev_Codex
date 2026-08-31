"""Li et al. fidelity and combined-infidelity formulas."""

from __future__ import annotations


def _validate_probability(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")


def combined_infidelity(epsilon_s: float, epsilon_meas: float) -> float:
    """Return the exact Li Eq. 30 combined infidelity.

    The small-error approximation is deliberately not used here.
    """

    _validate_probability("epsilon_s", epsilon_s)
    _validate_probability("epsilon_meas", epsilon_meas)
    return 1.0 - (1.0 - 4.0 * epsilon_s / 3.0) * (1.0 - 2.0 * epsilon_meas) ** 2


def combined_infidelity_small_error_approx(
    epsilon_s: float,
    epsilon_meas: float,
) -> float:
    """Return Li Eq. 30's displayed small-error approximation."""

    _validate_probability("epsilon_s", epsilon_s)
    _validate_probability("epsilon_meas", epsilon_meas)
    return 4.0 * (epsilon_s / 3.0 + epsilon_meas)


def fidelity_threshold(classical_bias: float, quantum_bias: float) -> float:
    """Return epsilon_th(M) = 1 - C(M)/Q(M), Li Eq. 37."""

    if quantum_bias <= 0.0:
        raise ValueError("quantum bias Q(M) must be positive")
    return 1.0 - classical_bias / quantum_bias


def noisy_quantum_value(epsilon: float, quantum_bias: float) -> float:
    """Return omega_Q(epsilon,M), Li Eq. 31."""

    _validate_probability("epsilon", epsilon)
    return (1.0 + (1.0 - epsilon) * quantum_bias) / 2.0


def noisy_gap(epsilon: float, classical_bias: float, quantum_bias: float) -> float:
    """Return Delta omega(epsilon,M), Li Eq. 34."""

    _validate_probability("epsilon", epsilon)
    return ((1.0 - epsilon) * quantum_bias - classical_bias) / 2.0
