"""Li et al. fidelity and combined-infidelity formulas."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray


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


def singlet_density_matrix() -> NDArray[np.complex128]:
    """Return |Psi-><Psi-| in the computational basis."""

    singlet = np.array([0.0, 1.0, -1.0, 0.0], dtype=np.complex128) / np.sqrt(2.0)
    return np.outer(singlet, singlet.conjugate())


def werner_state(epsilon_s: float) -> NDArray[np.complex128]:
    """Return the Bell-diagonal state-infidelity model in Li Eq. 26."""

    _validate_probability("epsilon_s", epsilon_s)
    singlet = singlet_density_matrix()
    identity = np.eye(4, dtype=np.complex128)
    return (1.0 - epsilon_s) * singlet + (epsilon_s / 3.0) * (identity - singlet)


def measurement_visibility(epsilon_meas: float) -> float:
    """Return the binary readout visibility from Li Eqs. 28-29."""

    _validate_probability("epsilon_meas", epsilon_meas)
    return 1.0 - 2.0 * epsilon_meas


def _measurement_axis(name: str, axis: Sequence[float]) -> NDArray[np.float64]:
    vector = np.asarray(axis, dtype=np.float64)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite three-dimensional vector")
    if not np.isclose(np.linalg.norm(vector), 1.0, atol=1e-12, rtol=0.0):
        raise ValueError(f"{name} must be a unit vector")
    return vector


def noisy_singlet_correlator(
    epsilon_s: float,
    epsilon_meas: float,
    alice_axis: Sequence[float],
    bob_axis: Sequence[float],
) -> float:
    """Evaluate Li Eqs. 26 and 28-29 directly by a density-matrix trace."""

    alice = _measurement_axis("alice_axis", alice_axis)
    bob = _measurement_axis("bob_axis", bob_axis)
    pauli = (
        np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128),
        np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128),
        np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128),
    )
    alice_observable = sum(component * matrix for component, matrix in zip(alice, pauli))
    bob_observable = sum(component * matrix for component, matrix in zip(bob, pauli))
    visibility = measurement_visibility(epsilon_meas)
    joint_observable = np.kron(
        visibility * alice_observable,
        visibility * bob_observable,
    )
    correlator = np.trace(werner_state(epsilon_s) @ joint_observable)
    if abs(float(correlator.imag)) > 1e-12:
        raise ArithmeticError("correlator has an unexpected imaginary component")
    return float(correlator.real)


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
