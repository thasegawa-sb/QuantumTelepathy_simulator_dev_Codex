"""Classical baselines from deterministic local strategies."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import product

from quantum_telepathy.core.nonlocal_game import Observation, validate_input_distribution

Decision = tuple[int, ...]
LocalStrategy = Mapping[int, int]
JointStrategy = tuple[LocalStrategy, ...]
UtilityFunction = Callable[[Observation, Decision], float]


@dataclass(frozen=True)
class ClassicalOptimizationResult:
    """Maximum value and strategy for deterministic local classical strategies."""

    value: float
    strategy: JointStrategy
    strategy_count: int


def local_deterministic_strategies(
    observations: Sequence[int],
    decisions: Sequence[int],
) -> Iterable[LocalStrategy]:
    """Yield all local maps from observations to decisions."""

    if not observations:
        raise ValueError("each party must have at least one observation")
    if not decisions:
        raise ValueError("each party must have at least one decision")
    for outputs in product(decisions, repeat=len(observations)):
        yield dict(zip(observations, outputs, strict=True))


def deterministic_joint_strategies(
    observation_sets: Sequence[Sequence[int]],
    decision_sets: Sequence[Sequence[int]],
) -> Iterable[JointStrategy]:
    """Yield all products of local deterministic strategies."""

    if len(observation_sets) != len(decision_sets):
        raise ValueError("observation_sets and decision_sets must have same length")
    per_party = [
        list(local_deterministic_strategies(observations, decisions))
        for observations, decisions in zip(observation_sets, decision_sets, strict=True)
    ]
    for strategies in product(*per_party):
        yield tuple(strategies)


def deterministic_strategy_value(
    strategy: JointStrategy,
    input_distribution: Mapping[Observation, float],
    utility: UtilityFunction,
) -> float:
    """Evaluate a deterministic local strategy."""

    validate_input_distribution(input_distribution)
    total = 0.0
    for observation, probability in input_distribution.items():
        if len(observation) != len(strategy):
            raise ValueError("observation arity does not match strategy arity")
        decision = tuple(
            local_strategy[local_observation]
            for local_strategy, local_observation in zip(strategy, observation, strict=True)
        )
        total += probability * float(utility(observation, decision))
    return total


def maximize_classical_value(
    observation_sets: Sequence[Sequence[int]],
    decision_sets: Sequence[Sequence[int]],
    input_distribution: Mapping[Observation, float],
    utility: UtilityFunction,
) -> ClassicalOptimizationResult:
    """Maximize expected utility over deterministic local strategies.

    Shared randomness cannot increase the optimum beyond this maximum because the
    classical local set is the convex hull of deterministic local strategies.
    """

    best_value = float("-inf")
    best_strategy: JointStrategy | None = None
    strategy_count = 0
    for strategy in deterministic_joint_strategies(observation_sets, decision_sets):
        strategy_count += 1
        value = deterministic_strategy_value(strategy, input_distribution, utility)
        if value > best_value:
            best_value = value
            best_strategy = strategy
    if best_strategy is None:
        raise ValueError("no deterministic strategies generated")
    return ClassicalOptimizationResult(best_value, best_strategy, strategy_count)
