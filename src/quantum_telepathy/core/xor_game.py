"""Two-party binary XOR-game primitives and CHSH oracles."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product
from typing import TypeAlias

Matrix2x2: TypeAlias = tuple[tuple[float, float], tuple[float, float]]
ParityUtility2x2: TypeAlias = tuple[
    tuple[tuple[float, float], tuple[float, float]],
    tuple[tuple[float, float], tuple[float, float]],
]


@dataclass(frozen=True)
class XORValueResult:
    """Classical and quantum values for a normalized XOR game."""

    classical_bias: float
    quantum_bias: float
    classical_value: float
    quantum_value: float
    gap: float


def uniform_distribution() -> Matrix2x2:
    """Return P(x,y)=1/4 for binary inputs."""

    return ((0.25, 0.25), (0.25, 0.25))


def independent_bernoulli_distribution(p: float) -> Matrix2x2:
    """Return P(x,y)=P(x)P(y), P(x=1)=P(y=1)=p."""

    if not 0.0 <= p <= 1.0:
        raise ValueError("p must be in [0, 1]")
    return (((1.0 - p) ** 2, (1.0 - p) * p), (p * (1.0 - p), p**2))


def validate_distribution2x2(distribution: Matrix2x2, *, tolerance: float = 1e-12) -> None:
    """Validate a binary input distribution."""

    values = [distribution[x][y] for x in range(2) for y in range(2)]
    if any(value < 0.0 for value in values):
        raise ValueError("input probabilities must be nonnegative")
    total = sum(values)
    if abs(total - 1.0) > tolerance:
        raise ValueError(f"input probabilities sum to {total}, not 1")


def chsh_matrix() -> Matrix2x2:
    """Return Li Eq. 35, M_CHSH = 1/4 [[1, 1], [1, -1]]."""

    return ((0.25, 0.25), (0.25, -0.25))


def xor_game_matrix(
    input_distribution: Matrix2x2,
    utility: ParityUtility2x2,
) -> Matrix2x2:
    """Build M_xy = P(x,y) * sum_o (-1)^o u(o|x,y)."""

    validate_distribution2x2(input_distribution)
    return tuple(
        tuple(
            input_distribution[x][y] * (float(utility[x][y][0]) - float(utility[x][y][1]))
            for y in range(2)
        )
        for x in range(2)
    )  # type: ignore[return-value]


def classical_bias(matrix: Matrix2x2) -> float:
    """Compute C(M) by enumerating all deterministic sign strategies."""

    best = float("-inf")
    for a0, a1, b0, b1 in product((-1.0, 1.0), repeat=4):
        alice = (a0, a1)
        bob = (b0, b1)
        value = sum(matrix[x][y] * alice[x] * bob[y] for x in range(2) for y in range(2))
        best = max(best, value)
    return best


def _row_norm(m0: float, m1: float, bob_inner_product: float) -> float:
    radicand = m0 * m0 + m1 * m1 + 2.0 * m0 * m1 * bob_inner_product
    if radicand < 0.0 and radicand > -1e-15:
        radicand = 0.0
    if radicand < 0.0:
        raise ArithmeticError(f"negative radicand {radicand}")
    return math.sqrt(radicand)


def quantum_bias_2x2(matrix: Matrix2x2) -> float:
    """Compute Q(M) for a two-input XOR game by one-dimensional optimization.

    For fixed Bob unit vectors b0,b1 with inner product c, Alice's optimal
    vector for row x aligns with M[x,0] b0 + M[x,1] b1. This reduces the
    Tsirelson vector optimization to maximizing over c in [-1, 1].
    """

    def objective(c: float) -> float:
        return _row_norm(matrix[0][0], matrix[0][1], c) + _row_norm(
            matrix[1][0], matrix[1][1], c
        )

    lower = -1.0
    upper = 1.0
    inv_phi = (math.sqrt(5.0) - 1.0) / 2.0
    left = upper - inv_phi * (upper - lower)
    right = lower + inv_phi * (upper - lower)
    f_left = objective(left)
    f_right = objective(right)

    for _ in range(200):
        if f_left < f_right:
            lower = left
            left = right
            f_left = f_right
            right = lower + inv_phi * (upper - lower)
            f_right = objective(right)
        else:
            upper = right
            right = left
            f_right = f_left
            left = upper - inv_phi * (upper - lower)
            f_left = objective(left)

    midpoint = (lower + upper) / 2.0
    return max(objective(-1.0), objective(1.0), objective(midpoint), f_left, f_right)


def classical_value(matrix: Matrix2x2) -> float:
    """Return omega_C(M) = (1 + C(M))/2 for normalized XOR utilities."""

    return (1.0 + classical_bias(matrix)) / 2.0


def quantum_value(matrix: Matrix2x2) -> float:
    """Return omega_Q(M) = (1 + Q(M))/2 for normalized XOR utilities."""

    return (1.0 + quantum_bias_2x2(matrix)) / 2.0


def gap(matrix: Matrix2x2) -> float:
    """Return omega_Q - omega_C for a normalized two-input XOR game."""

    return quantum_value(matrix) - classical_value(matrix)


def chsh_values() -> XORValueResult:
    """Return the canonical CHSH classical/quantum values and gap."""

    matrix = chsh_matrix()
    c_bias = classical_bias(matrix)
    q_bias = quantum_bias_2x2(matrix)
    c_value = (1.0 + c_bias) / 2.0
    q_value = (1.0 + q_bias) / 2.0
    return XORValueResult(c_bias, q_bias, c_value, q_value, q_value - c_value)
