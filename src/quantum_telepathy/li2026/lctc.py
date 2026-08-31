"""Li et al. generalized two-party LCTC utility model."""

from __future__ import annotations

from quantum_telepathy.core.xor_game import Matrix2x2, ParityUtility2x2, xor_game_matrix


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


def check_latency_constraint(t_loc: float, t_comm: float) -> bool:
    """Return True exactly when Li Eq. 15, T_loc < T_comm, holds."""

    if t_loc < 0.0 or t_comm < 0.0:
        raise ValueError("timing values must be nonnegative")
    return t_loc < t_comm
