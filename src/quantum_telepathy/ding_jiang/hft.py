"""Ding-Jiang v3 HFT/hedging utility model."""

from __future__ import annotations

import math

from quantum_telepathy.core.xor_game import (
    Matrix2x2,
    ParityUtility2x2,
    XORValueResult,
    classical_bias,
    independent_bernoulli_distribution,
    quantum_bias_2x2,
    xor_game_matrix,
)


def hedging_utility(beta: float) -> ParityUtility2x2:
    """Return Ding-Jiang Eq. 3.1 as u(o|x,y), with o=a xor b.

    Inputs x,y use 0=N and 1=I. Output parity o=0 means same ordering and
    o=1 means different ordering.
    """

    if not 0.0 <= beta <= 1.0:
        raise ValueError("beta must be in [0, 1]")
    return (
        ((0.0, 1.0), (beta, 1.0 - beta)),
        ((beta, 1.0 - beta), (1.0, 0.0)),
    )


def hedging_matrix(p: float, beta: float) -> Matrix2x2:
    """Return the weighted XOR matrix for the Ding-Jiang hedging problem."""

    return xor_game_matrix(independent_bernoulli_distribution(p), hedging_utility(beta))


def biased_chsh_values(p: float) -> XORValueResult:
    """Return Ding-Jiang Theorem 10 values for beta=0 biased CHSH."""

    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be in [0, 1]")
    if p <= 0.5:
        classical = 1.0 - p**2
    else:
        classical = -(p**2) + 2.0 * p

    lower = 1.0 - 1.0 / math.sqrt(2.0)
    upper = 1.0 / math.sqrt(2.0)
    if p <= lower:
        quantum = 1.0 - p**2
    elif p <= upper:
        quantum = (1.0 / math.sqrt(2.0)) * (1.0 - 2.0 * p * (1.0 - p)) + 0.5
    else:
        quantum = -(p**2) + 2.0 * p

    return XORValueResult(
        classical_bias=2.0 * classical - 1.0,
        quantum_bias=2.0 * quantum - 1.0,
        classical_value=classical,
        quantum_value=quantum,
        gap=quantum - classical,
    )


def ideal_hedging_values(p: float, beta: float) -> XORValueResult:
    """Compute ideal Ding-Jiang hedging values from the shared XOR core."""

    matrix = hedging_matrix(p, beta)
    c_bias = classical_bias(matrix)
    q_bias = quantum_bias_2x2(matrix)
    c_value = (1.0 + c_bias) / 2.0
    q_value = (1.0 + q_bias) / 2.0
    return XORValueResult(c_bias, q_bias, c_value, q_value, q_value - c_value)
