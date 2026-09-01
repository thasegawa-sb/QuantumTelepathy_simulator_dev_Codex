"""Ding-Jiang v3 Figure 3 evaluation and classical cross-validation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from quantum_telepathy.core.classical import maximize_classical_value
from quantum_telepathy.core.xor_game import independent_bernoulli_distribution
from quantum_telepathy.ding_jiang.hft import hedging_utility, ideal_hedging_values


@dataclass(frozen=True)
class Fig3Point:
    """One ideal hedging-game point in the Figure 3 parameter plane."""

    p: float
    beta: float
    classical_value: float
    quantum_value: float
    gap: float
    classical_oracle_value: float
    classical_oracle_abs_error: float
    deterministic_strategy_count: int


def independent_classical_value(p: float, beta: float) -> tuple[float, int]:
    """Compute the classical value through the generic local-strategy path."""

    distribution = independent_bernoulli_distribution(p)
    utility_table = hedging_utility(beta)
    input_distribution = {
        (x, y): distribution[x][y] for x in range(2) for y in range(2)
    }

    def utility(observation: tuple[int, ...], decision: tuple[int, ...]) -> float:
        x, y = observation
        a, b = decision
        return utility_table[x][y][a ^ b]

    result = maximize_classical_value(
        observation_sets=((0, 1), (0, 1)),
        decision_sets=((0, 1), (0, 1)),
        input_distribution=input_distribution,
        utility=utility,
    )
    return result.value, result.strategy_count


def evaluate_fig3_point(
    p: float,
    beta: float,
    *,
    classical_tolerance: float = 1e-12,
) -> Fig3Point:
    """Evaluate one point and require agreement with the classical oracle."""

    if classical_tolerance < 0.0:
        raise ValueError("classical_tolerance must be nonnegative")
    values = ideal_hedging_values(p, beta)
    oracle_value, strategy_count = independent_classical_value(p, beta)
    oracle_error = abs(values.classical_value - oracle_value)
    if oracle_error > classical_tolerance:
        raise ArithmeticError(
            "XOR and deterministic classical values disagree: "
            f"p={p}, beta={beta}, error={oracle_error}"
        )
    return Fig3Point(
        p=p,
        beta=beta,
        classical_value=values.classical_value,
        quantum_value=values.quantum_value,
        gap=values.gap,
        classical_oracle_value=oracle_value,
        classical_oracle_abs_error=oracle_error,
        deterministic_strategy_count=strategy_count,
    )


def evaluate_fig3_grid(
    p_values: Iterable[float],
    beta_values: Iterable[float],
    *,
    classical_tolerance: float = 1e-12,
) -> tuple[Fig3Point, ...]:
    """Evaluate a beta-major Figure 3 grid."""

    ps = tuple(p_values)
    betas = tuple(beta_values)
    if not ps or not betas:
        raise ValueError("p_values and beta_values must not be empty")
    return tuple(
        evaluate_fig3_point(p, beta, classical_tolerance=classical_tolerance)
        for beta in betas
        for p in ps
    )
