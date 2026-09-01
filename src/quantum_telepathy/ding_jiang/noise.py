"""Ding-Jiang v3 qubit depolarizing-noise model from Section 4.2."""

from __future__ import annotations

import math
from itertools import product

from quantum_telepathy.core.nonlocal_game import Behavior, Decision, Observation

_BINARY_DECISIONS = tuple(product((0, 1), repeat=2))


def _validate_probability(value: float, name: str) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")


def depolarize_qubit_behavior(
    behavior: Behavior,
    nu: float,
) -> dict[Observation, dict[Decision, float]]:
    """Apply paper Eq. 4.2, ``P -> (1-nu)P + nu/4``.

    This is the paper's two-party, binary-output, rank-one qubit case. It is
    not the general rank-dependent behavior in Appendix A.4.
    """

    _validate_probability(nu, "nu")
    if not behavior:
        raise ValueError("behavior must not be empty")
    expected_decisions = set(_BINARY_DECISIONS)
    result: dict[Observation, dict[Decision, float]] = {}
    for observation, conditional in behavior.items():
        if set(conditional) != expected_decisions:
            raise ValueError(
                "each observation must define all four binary decision pairs"
            )
        total = 0.0
        noisy_conditional: dict[Decision, float] = {}
        for decision in _BINARY_DECISIONS:
            probability = float(conditional[decision])
            _validate_probability(
                probability,
                f"behavior probability at {observation!r}, {decision!r}",
            )
            total += probability
            noisy_conditional[decision] = (1.0 - nu) * probability + nu / 4.0
        if abs(total - 1.0) > 1e-12:
            raise ValueError(
                f"conditional probabilities for {observation!r} sum to {total}, not 1"
            )
        result[observation] = noisy_conditional
    return result


def noisy_hedging_quantum_value(noiseless_quantum_value: float, nu: float) -> float:
    """Apply paper Eq. 4.3, ``q_nu = (1-nu) q + nu/2``."""

    _validate_probability(noiseless_quantum_value, "noiseless_quantum_value")
    _validate_probability(nu, "nu")
    return (1.0 - nu) * noiseless_quantum_value + nu / 2.0


def noisy_hedging_gap(
    classical_value: float,
    noiseless_quantum_value: float,
    nu: float,
) -> float:
    """Return the signed advantage of the paper's fixed noisy qubit strategy."""

    _validate_probability(classical_value, "classical_value")
    return noisy_hedging_quantum_value(noiseless_quantum_value, nu) - classical_value


def depolarizing_robustness(
    classical_value: float,
    noiseless_quantum_value: float,
    *,
    advantage_tolerance: float = 1e-12,
) -> float:
    """Return paper ``nu_star=(q_star-c_star)/(q_star-1/2)``.

    The paper defines zero robustness when there is no noiseless quantum
    advantage. For an advantageous hedging point, Section 4.2 proves that the
    denominator is positive.
    """

    _validate_probability(classical_value, "classical_value")
    _validate_probability(noiseless_quantum_value, "noiseless_quantum_value")
    if not math.isfinite(advantage_tolerance) or advantage_tolerance < 0.0:
        raise ValueError("advantage_tolerance must be finite and nonnegative")
    advantage = noiseless_quantum_value - classical_value
    if advantage <= advantage_tolerance:
        return 0.0
    denominator = noiseless_quantum_value - 0.5
    if denominator <= 0.0:
        raise ValueError("an advantageous hedging value must exceed 1/2")
    robustness = advantage / denominator
    if robustness > 1.0 + 1e-12:
        raise ValueError("computed robustness lies above 1")
    return min(1.0, robustness)
