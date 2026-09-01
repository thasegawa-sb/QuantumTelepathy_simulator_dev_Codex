"""Ding-Jiang v3 direct-photon loss model from Eq. A.11 and A.12."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from quantum_telepathy.core.xor_game import (
    Matrix2x2,
    ParityUtility2x2,
    validate_distribution2x2,
)

RealMatrix: TypeAlias = NDArray[np.float64]
RealVector: TypeAlias = NDArray[np.float64]
LocalFallback: TypeAlias = tuple[int, int]
FallbackStrategy: TypeAlias = tuple[LocalFallback, LocalFallback]


@dataclass(frozen=True)
class LossyOptimizationResult:
    """Maximum lossy utility and an attaining qubit strategy."""

    value: float
    efficiencies: tuple[float, float]
    angles: tuple[float, float]
    fallback_strategy: FallbackStrategy
    state: tuple[float, float, float, float]
    grid_size: int
    local_starts: int
    objective_evaluations: int


@dataclass(frozen=True)
class ThresholdEvaluation:
    """One lossy-value evaluation made during threshold bisection."""

    efficiency: float
    quantum_value: float
    advantage: float


@dataclass(frozen=True)
class LossThresholdResult:
    """Transition found by the configured explicit-strategy optimizer.

    The upper endpoint exhibits a strategy with positive advantage and therefore
    upper-bounds the physical threshold. The lower endpoint only records that
    this optimizer did not detect an advantage; it is not an independent lower
    bound on the physical threshold.
    """

    threshold: float
    lower_bound: float
    upper_bound: float
    classical_value: float
    advantage_tolerance: float
    evaluations: tuple[ThresholdEvaluation, ...]


def _validate_probability(value: float, name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")


def _validate_fallback(fallback_strategy: FallbackStrategy) -> None:
    if len(fallback_strategy) != 2 or any(len(local) != 2 for local in fallback_strategy):
        raise ValueError("fallback_strategy must contain two binary local maps")
    if any(output not in (0, 1) for local in fallback_strategy for output in local):
        raise ValueError("fallback outputs must be 0 or 1")


def projective_measurement(angle: float) -> tuple[RealMatrix, RealMatrix]:
    """Return the paper's binary qubit measurement at angle ``angle``."""

    vector = np.array((math.cos(angle), -math.sin(angle)), dtype=float)
    zero_projector = np.outer(vector, vector)
    return zero_projector, np.eye(2, dtype=float) - zero_projector


def _measurements(angle: float) -> tuple[tuple[RealMatrix, RealMatrix], ...]:
    return (projective_measurement(0.0), projective_measurement(angle))


def lossy_bell_operator(
    input_distribution: Matrix2x2,
    utility: ParityUtility2x2,
    efficiencies: tuple[float, float],
    angles: tuple[float, float],
    fallback_strategy: FallbackStrategy,
) -> RealMatrix:
    """Construct the two-party lossy Bell operator in Ding-Jiang Eq. A.12."""

    validate_distribution2x2(input_distribution)
    eta_alice, eta_bob = efficiencies
    _validate_probability(eta_alice, "Alice efficiency")
    _validate_probability(eta_bob, "Bob efficiency")
    _validate_fallback(fallback_strategy)
    alice_measurements = _measurements(angles[0])
    bob_measurements = _measurements(angles[1])
    identity = np.eye(2, dtype=float)
    # Expanding these local effective POVMs gives the four loss subsets in A.12.
    alice_effects = tuple(
        tuple(
            eta_alice * alice_measurements[x][a]
            + (1.0 - eta_alice)
            * float(a == fallback_strategy[0][x])
            * identity
            for a in range(2)
        )
        for x in range(2)
    )
    bob_effects = tuple(
        tuple(
            eta_bob * bob_measurements[y][b]
            + (1.0 - eta_bob) * float(b == fallback_strategy[1][y]) * identity
            for b in range(2)
        )
        for y in range(2)
    )
    operator = np.zeros((4, 4), dtype=float)
    for x, y, a, b in product(range(2), repeat=4):
        operator += (
            input_distribution[x][y]
            * utility[x][y][a ^ b]
            * np.kron(alice_effects[x][a], bob_effects[y][b])
        )
    return (operator + operator.T) / 2.0


def _normalized_state(state: tuple[float, ...] | RealVector) -> RealVector:
    vector = np.asarray(state, dtype=float)
    if vector.shape != (4,):
        raise ValueError("state must have four amplitudes")
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise ValueError("state must be nonzero")
    return vector / norm


def lossy_expected_utility(
    input_distribution: Matrix2x2,
    utility: ParityUtility2x2,
    efficiencies: tuple[float, float],
    angles: tuple[float, float],
    fallback_strategy: FallbackStrategy,
    state: tuple[float, ...] | RealVector,
) -> float:
    """Evaluate Eq. A.11 directly as a mixture of loss-event probabilities."""

    validate_distribution2x2(input_distribution)
    eta_alice, eta_bob = efficiencies
    _validate_probability(eta_alice, "Alice efficiency")
    _validate_probability(eta_bob, "Bob efficiency")
    _validate_fallback(fallback_strategy)
    vector = _normalized_state(state)
    alice_measurements = _measurements(angles[0])
    bob_measurements = _measurements(angles[1])
    identity = np.eye(2, dtype=float)
    total = 0.0

    for x, y, a, b in product(range(2), repeat=4):
        alice_projector = alice_measurements[x][a]
        bob_projector = bob_measurements[y][b]
        both_received = float(vector @ np.kron(alice_projector, bob_projector) @ vector)
        bob_received = (
            float(vector @ np.kron(identity, bob_projector) @ vector)
            if a == fallback_strategy[0][x]
            else 0.0
        )
        alice_received = (
            float(vector @ np.kron(alice_projector, identity) @ vector)
            if b == fallback_strategy[1][y]
            else 0.0
        )
        both_lost = float(
            a == fallback_strategy[0][x] and b == fallback_strategy[1][y]
        )
        probability = (
            eta_alice * eta_bob * both_received
            + (1.0 - eta_alice) * eta_bob * bob_received
            + eta_alice * (1.0 - eta_bob) * alice_received
            + (1.0 - eta_alice) * (1.0 - eta_bob) * both_lost
        )
        total += input_distribution[x][y] * utility[x][y][a ^ b] * probability
    return total


def _largest_eigenpair(operator: RealMatrix) -> tuple[float, RealVector]:
    eigenvalues, eigenvectors = np.linalg.eigh(operator)
    state = eigenvectors[:, -1]
    first_nonzero = next((value for value in state if abs(value) > 1e-14), 1.0)
    if first_nonzero < 0.0:
        state = -state
    return float(eigenvalues[-1]), state


def _fallback_strategies() -> tuple[FallbackStrategy, ...]:
    return tuple(
        ((bits[0], bits[1]), (bits[2], bits[3]))
        for bits in product((0, 1), repeat=4)
    )


def optimize_lossy_value(
    input_distribution: Matrix2x2,
    utility: ParityUtility2x2,
    efficiencies: tuple[float, float],
    *,
    grid_size: int = 20,
    local_starts: int = 2,
    optimizer_tolerance: float = 1e-11,
) -> LossyOptimizationResult:
    """Optimize Eq. A.12 over two angles and all 16 fallback strategies."""

    if grid_size < 2:
        raise ValueError("grid_size must be at least 2")
    if local_starts < 1:
        raise ValueError("local_starts must be positive")
    if optimizer_tolerance <= 0.0:
        raise ValueError("optimizer_tolerance must be positive")
    for index, efficiency in enumerate(efficiencies):
        _validate_probability(efficiency, f"efficiency {index}")

    angle_grid = np.linspace(-math.pi / 2.0, math.pi / 2.0, grid_size, endpoint=False)
    bounds = ((-math.pi / 2.0, math.pi / 2.0),) * 2
    best_value = float("-inf")
    best_angles = (0.0, 0.0)
    best_fallback: FallbackStrategy = ((0, 0), (0, 0))
    best_state = np.array((1.0, 0.0, 0.0, 0.0))
    evaluation_count = 0

    for fallback in _fallback_strategies():
        grid_candidates: list[tuple[float, tuple[float, float]]] = []
        for alice_angle, bob_angle in product(angle_grid, repeat=2):
            operator = lossy_bell_operator(
                input_distribution,
                utility,
                efficiencies,
                (float(alice_angle), float(bob_angle)),
                fallback,
            )
            value = float(np.linalg.eigvalsh(operator)[-1])
            evaluation_count += 1
            grid_candidates.append((value, (float(alice_angle), float(bob_angle))))
        grid_candidates.sort(key=lambda candidate: candidate[0], reverse=True)

        for _, initial_angles in grid_candidates[:local_starts]:
            result = minimize(
                lambda candidate: -float(
                    np.linalg.eigvalsh(
                        lossy_bell_operator(
                            input_distribution,
                            utility,
                            efficiencies,
                            (float(candidate[0]), float(candidate[1])),
                            fallback,
                        )
                    )[-1]
                ),
                x0=np.asarray(initial_angles),
                method="Powell",
                bounds=bounds,
                options={
                    "xtol": optimizer_tolerance,
                    "ftol": optimizer_tolerance,
                    "maxiter": 500,
                },
            )
            evaluation_count += int(result.nfev)
            if not result.success:
                raise RuntimeError(f"lossy angle optimization failed: {result.message}")
            candidate_angles = (float(result.x[0]), float(result.x[1]))
            candidate_operator = lossy_bell_operator(
                input_distribution,
                utility,
                efficiencies,
                candidate_angles,
                fallback,
            )
            candidate_value, candidate_state = _largest_eigenpair(candidate_operator)
            evaluation_count += 1
            if candidate_value > best_value + 1e-14:
                best_value = candidate_value
                best_angles = candidate_angles
                best_fallback = fallback
                best_state = candidate_state

    return LossyOptimizationResult(
        value=best_value,
        efficiencies=efficiencies,
        angles=best_angles,
        fallback_strategy=best_fallback,
        state=(
            float(best_state[0]),
            float(best_state[1]),
            float(best_state[2]),
            float(best_state[3]),
        ),
        grid_size=grid_size,
        local_starts=local_starts,
        objective_evaluations=evaluation_count,
    )


def find_loss_threshold(
    input_distribution: Matrix2x2,
    utility: ParityUtility2x2,
    classical_value: float,
    *,
    lower_efficiency: float = 2.0 / 3.0,
    upper_efficiency: float = 1.0,
    efficiency_tolerance: float = 1e-5,
    advantage_tolerance: float = 1e-10,
    grid_size: int = 20,
    local_starts: int = 2,
    optimizer_tolerance: float = 1e-11,
) -> LossThresholdResult:
    """Bracket the minimum equal efficiency yielding detectable advantage."""

    _validate_probability(lower_efficiency, "lower_efficiency")
    _validate_probability(upper_efficiency, "upper_efficiency")
    if lower_efficiency >= upper_efficiency:
        raise ValueError("lower_efficiency must be less than upper_efficiency")
    if efficiency_tolerance <= 0.0 or advantage_tolerance < 0.0:
        raise ValueError("threshold tolerances are invalid")

    evaluations: list[ThresholdEvaluation] = []

    def evaluate(efficiency: float) -> float:
        result = optimize_lossy_value(
            input_distribution,
            utility,
            (efficiency, efficiency),
            grid_size=grid_size,
            local_starts=local_starts,
            optimizer_tolerance=optimizer_tolerance,
        )
        advantage = result.value - classical_value
        evaluations.append(ThresholdEvaluation(efficiency, result.value, advantage))
        return advantage

    lower = lower_efficiency
    upper = upper_efficiency
    upper_advantage = evaluate(upper)
    if upper_advantage <= advantage_tolerance:
        return LossThresholdResult(
            threshold=1.0,
            lower_bound=1.0,
            upper_bound=1.0,
            classical_value=classical_value,
            advantage_tolerance=advantage_tolerance,
            evaluations=tuple(evaluations),
        )
    lower_advantage = evaluate(lower)
    if lower_advantage > advantage_tolerance:
        raise ValueError("lower_efficiency already has detectable quantum advantage")

    while upper - lower > efficiency_tolerance:
        midpoint = (lower + upper) / 2.0
        if evaluate(midpoint) > advantage_tolerance:
            upper = midpoint
        else:
            lower = midpoint

    return LossThresholdResult(
        threshold=(lower + upper) / 2.0,
        lower_bound=lower,
        upper_bound=upper,
        classical_value=classical_value,
        advantage_tolerance=advantage_tolerance,
        evaluations=tuple(evaluations),
    )


def schmidt_coefficients(state: tuple[float, ...] | RealVector) -> tuple[float, float]:
    """Return descending Schmidt coefficients for a two-qubit pure state."""

    matrix = _normalized_state(state).reshape((2, 2))
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    return float(singular_values[0]), float(singular_values[1])
