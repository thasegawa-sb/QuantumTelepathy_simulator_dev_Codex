"""Generic finite nonlocal-game utilities."""

from __future__ import annotations

from collections.abc import Callable, Mapping

Observation = tuple[int, ...]
Decision = tuple[int, ...]
Behavior = Mapping[Observation, Mapping[Decision, float]]
UtilityFunction = Callable[[Observation, Decision], float]


def expected_utility(
    input_distribution: Mapping[Observation, float],
    behavior: Behavior,
    utility: UtilityFunction,
) -> float:
    """Evaluate sum_o P(o) sum_d P(d|o) u(d|o)."""

    total = 0.0
    for observation, observation_probability in input_distribution.items():
        if observation_probability < 0.0:
            raise ValueError(f"negative input probability for {observation!r}")
        conditional = behavior[observation]
        conditional_total = sum(conditional.values())
        if abs(conditional_total - 1.0) > 1e-12:
            raise ValueError(
                f"conditional probabilities for {observation!r} sum to "
                f"{conditional_total}, not 1"
            )
        for decision, decision_probability in conditional.items():
            if decision_probability < 0.0:
                raise ValueError(
                    f"negative decision probability for {decision!r} at {observation!r}"
                )
            total += (
                observation_probability
                * decision_probability
                * float(utility(observation, decision))
            )
    return total


def validate_input_distribution(
    input_distribution: Mapping[Observation, float],
    *,
    tolerance: float = 1e-12,
) -> None:
    """Validate a finite input distribution over observation tuples."""

    if not input_distribution:
        raise ValueError("input distribution must not be empty")
    total = 0.0
    for observation, probability in input_distribution.items():
        if not isinstance(observation, tuple):
            raise TypeError("observations must be tuples")
        if probability < 0.0:
            raise ValueError(f"negative probability for observation {observation!r}")
        total += probability
    if abs(total - 1.0) > tolerance:
        raise ValueError(f"input probabilities sum to {total}, not 1")
