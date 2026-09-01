"""Li et al. generalized two-party LCTC utility model."""

from __future__ import annotations

from quantum_telepathy.core.classical import (
    ClassicalOptimizationResult,
    maximize_classical_value,
)
from quantum_telepathy.core.xor_game import (
    Matrix2x2,
    ParityUtility2x2,
    XORValueResult,
    classical_bias,
    quantum_bias_2x2,
    xor_game_matrix,
)


def generalized_lctc_utility(beta1: float, beta2: float) -> ParityUtility2x2:
    """Return Li Eq. 23/Eq. 24 as u(o|x,y), with o=a xor b."""

    if not 0.0 <= beta1 <= 1.0:
        raise ValueError("beta1 must be in [0, 1]")
    if not 0.0 <= beta2 <= 1.0:
        raise ValueError("beta2 must be in [0, 1]")
    return (
        ((1.0, 0.0), (1.0 - beta1, beta1)),
        ((1.0 - beta2, beta2), (0.0, 1.0)),
    )


def generalized_lctc_matrix(
    input_distribution: Matrix2x2,
    beta1: float,
    beta2: float,
) -> Matrix2x2:
    """Return Li Eq. 25, including the CHSH-consistent -P(1,1) entry."""

    return xor_game_matrix(input_distribution, generalized_lctc_utility(beta1, beta2))


def correlated_input_distribution(p11: float) -> Matrix2x2:
    """Return the correlated input family used in Li Figure 2(b).

    The family obeys P(1,1) = 2 P(0,1) = 2 P(1,0), with the remaining
    probability assigned to P(0,0). Normalization therefore requires
    0 <= P(1,1) <= 1/2.
    """

    if not 0.0 <= p11 <= 0.5:
        raise ValueError("p11 must be in [0, 0.5]")
    off_diagonal = p11 / 2.0
    return ((1.0 - 2.0 * p11, off_diagonal), (off_diagonal, p11))


def generalized_lctc_values(
    input_distribution: Matrix2x2,
    beta1: float,
    beta2: float,
) -> XORValueResult:
    """Return ideal classical and quantum values for Li Eqs. 24-25."""

    matrix = generalized_lctc_matrix(input_distribution, beta1, beta2)
    c_bias = classical_bias(matrix)
    q_bias = quantum_bias_2x2(matrix)
    c_value = (1.0 + c_bias) / 2.0
    q_value = (1.0 + q_bias) / 2.0
    return XORValueResult(c_bias, q_bias, c_value, q_value, q_value - c_value)


def enumerated_classical_optimum(
    input_distribution: Matrix2x2,
    beta1: float,
    beta2: float,
) -> ClassicalOptimizationResult:
    """Independently maximize Li utility over deterministic local strategies."""

    utility_table = generalized_lctc_utility(beta1, beta2)
    distribution = {
        (x, y): input_distribution[x][y] for x in range(2) for y in range(2)
    }

    def utility(observation: tuple[int, ...], decision: tuple[int, ...]) -> float:
        x, y = observation
        a, b = decision
        return utility_table[x][y][a ^ b]

    return maximize_classical_value(
        observation_sets=((0, 1), (0, 1)),
        decision_sets=((0, 1), (0, 1)),
        input_distribution=distribution,
        utility=utility,
    )


def check_latency_constraint(t_loc: float, t_comm: float) -> bool:
    """Return True exactly when Li Eq. 15, T_loc < T_comm, holds."""

    if t_loc < 0.0 or t_comm < 0.0:
        raise ValueError("timing values must be nonnegative")
    return t_loc < t_comm
