"""Independent NPA Q1+AB upper bounds for Ding-Jiang photon loss."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product
from time import perf_counter
from typing import TypeAlias

import cvxpy as cp
import numpy as np

from quantum_telepathy.core.xor_game import (
    Matrix2x2,
    ParityUtility2x2,
    validate_distribution2x2,
)
from quantum_telepathy.ding_jiang.loss import FallbackStrategy

RealPair: TypeAlias = tuple[float, float]
MomentWord: TypeAlias = tuple[tuple[int, ...], tuple[int, ...]]


@dataclass(frozen=True)
class LossyCorrelatorFunctional:
    """Bell functional in constant, marginal, and correlator coordinates."""

    constant: float
    alice: RealPair
    bob: RealPair
    correlator: Matrix2x2
    maximum_utility: float


@dataclass(frozen=True)
class FallbackNPAEvaluation:
    """One Q1+AB optimization for a fixed deterministic fallback."""

    fallback_strategy: FallbackStrategy
    raw_upper_bound: float
    guarded_upper_bound: float
    solver_status: str
    solve_time_s: float


@dataclass(frozen=True)
class NPAUpperBoundResult:
    """Maximum Q1+AB upper bound over all deterministic fallbacks."""

    efficiencies: tuple[float, float]
    upper_bound: float
    raw_upper_bound: float
    fallback_strategy: FallbackStrategy
    solver_error_margin: float
    relaxation: str
    solver: str
    evaluations: tuple[FallbackNPAEvaluation, ...]


@dataclass(frozen=True)
class NPAThresholdEvaluation:
    """One upper-bound evaluation made during threshold bisection."""

    efficiency: float
    quantum_upper_bound: float
    advantage_upper_bound: float
    solver_statuses: tuple[str, ...]


@dataclass(frozen=True)
class NPAThresholdLowerBoundResult:
    """Numerical lower bound on eta-star obtained from Q1+AB."""

    threshold_lower_bound: float
    transition_upper_bound: float
    classical_value: float
    efficiency_tolerance: float
    advantage_tolerance: float
    solver_error_margin: float
    evaluations: tuple[NPAThresholdEvaluation, ...]


def _validate_probability(value: float, name: str) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")


def _validate_fallback(fallback_strategy: FallbackStrategy) -> None:
    if len(fallback_strategy) != 2 or any(
        len(local) != 2 for local in fallback_strategy
    ):
        raise ValueError("fallback_strategy must contain two binary local maps")
    if any(
        output not in (0, 1)
        for local in fallback_strategy
        for output in local
    ):
        raise ValueError("fallback outputs must be 0 or 1")


def _fallback_strategies() -> tuple[FallbackStrategy, ...]:
    return tuple(
        ((bits[0], bits[1]), (bits[2], bits[3]))
        for bits in product((0, 1), repeat=4)
    )


def lossy_correlator_functional(
    input_distribution: Matrix2x2,
    utility: ParityUtility2x2,
    efficiencies: tuple[float, float],
    fallback_strategy: FallbackStrategy,
) -> LossyCorrelatorFunctional:
    """Expand Ding-Jiang Eq. A.11 into binary observable moments."""

    validate_distribution2x2(input_distribution)
    eta_alice, eta_bob = efficiencies
    _validate_probability(eta_alice, "Alice efficiency")
    _validate_probability(eta_bob, "Bob efficiency")
    _validate_fallback(fallback_strategy)
    constant = 0.0
    alice = [0.0, 0.0]
    bob = [0.0, 0.0]
    correlator = [[0.0, 0.0], [0.0, 0.0]]
    maximum_utility = float("-inf")

    for x, y in product(range(2), repeat=2):
        probability = input_distribution[x][y]
        utility_zero, utility_one = utility[x][y]
        maximum_utility = max(maximum_utility, utility_zero, utility_one)
        average_utility = (utility_zero + utility_one) / 2.0
        parity_coefficient = (utility_zero - utility_one) / 2.0
        alice_sign = 1.0 if fallback_strategy[0][x] == 0 else -1.0
        bob_sign = 1.0 if fallback_strategy[1][y] == 0 else -1.0
        constant += probability * (
            average_utility
            + parity_coefficient
            * (1.0 - eta_alice)
            * (1.0 - eta_bob)
            * alice_sign
            * bob_sign
        )
        alice[x] += (
            probability
            * parity_coefficient
            * eta_alice
            * (1.0 - eta_bob)
            * bob_sign
        )
        bob[y] += (
            probability
            * parity_coefficient
            * (1.0 - eta_alice)
            * eta_bob
            * alice_sign
        )
        correlator[x][y] += (
            probability * parity_coefficient * eta_alice * eta_bob
        )

    return LossyCorrelatorFunctional(
        constant=constant,
        alice=(alice[0], alice[1]),
        bob=(bob[0], bob[1]),
        correlator=(
            (correlator[0][0], correlator[0][1]),
            (correlator[1][0], correlator[1][1]),
        ),
        maximum_utility=maximum_utility,
    )


def evaluate_correlator_functional(
    functional: LossyCorrelatorFunctional,
    alice_marginals: RealPair,
    bob_marginals: RealPair,
    correlators: Matrix2x2,
) -> float:
    """Evaluate a lossy functional from ideal observable moments."""

    return (
        functional.constant
        + sum(functional.alice[x] * alice_marginals[x] for x in range(2))
        + sum(functional.bob[y] * bob_marginals[y] for y in range(2))
        + sum(
            functional.correlator[x][y] * correlators[x][y]
            for x, y in product(range(2), repeat=2)
        )
    )


def _reduce_involutions(sequence: tuple[int, ...]) -> tuple[int, ...]:
    reduced: list[int] = []
    for operator in sequence:
        if reduced and reduced[-1] == operator:
            reduced.pop()
        else:
            reduced.append(operator)
    return tuple(reduced)


def _adjoint_product(left: MomentWord, right: MomentWord) -> MomentWord:
    alice = _reduce_involutions(tuple(reversed(left[0])) + right[0])
    bob = _reduce_involutions(tuple(reversed(left[1])) + right[1])
    return alice, bob


_MOMENT_WORDS: tuple[MomentWord, ...] = (
    ((), ()),
    ((0,), ()),
    ((1,), ()),
    ((), (0,)),
    ((), (1,)),
    ((0,), (0,)),
    ((0,), (1,)),
    ((1,), (0,)),
    ((1,), (1,)),
)


class _NPAQ1ABProgram:
    """Reusable real Q1+AB moment relaxation for one Bell functional."""

    def __init__(self, solver: str, solver_tolerance: float) -> None:
        if solver != "CLARABEL":
            raise ValueError("the NPA implementation currently supports CLARABEL only")
        if solver not in cp.installed_solvers():
            raise ValueError(f"CVXPY solver {solver!r} is not installed")
        if not math.isfinite(solver_tolerance) or solver_tolerance <= 0.0:
            raise ValueError("solver_tolerance must be finite and positive")
        self.solver = solver
        self.solver_tolerance = solver_tolerance
        self.gamma = cp.Variable(
            (len(_MOMENT_WORDS), len(_MOMENT_WORDS)),
            symmetric=True,
        )
        self.coefficients = cp.Parameter(len(_MOMENT_WORDS))
        constraints: list[cp.Constraint] = [self.gamma >> 0]
        representatives: dict[MomentWord, tuple[int, int]] = {}
        for row, column in product(range(len(_MOMENT_WORDS)), repeat=2):
            canonical = _adjoint_product(
                _MOMENT_WORDS[row],
                _MOMENT_WORDS[column],
            )
            if canonical in representatives:
                first_row, first_column = representatives[canonical]
                constraints.append(
                    self.gamma[row, column]
                    == self.gamma[first_row, first_column]
                )
            else:
                representatives[canonical] = (row, column)
        constraints.append(self.gamma[0, 0] == 1.0)
        first_row = self.gamma[0, :]
        objective = cp.Maximize(self.coefficients @ first_row)
        self.problem = cp.Problem(objective, constraints)

    def solve(self, functional: LossyCorrelatorFunctional) -> tuple[float, str, float]:
        self.coefficients.value = np.asarray(
            (
                functional.constant,
                functional.alice[0],
                functional.alice[1],
                functional.bob[0],
                functional.bob[1],
                functional.correlator[0][0],
                functional.correlator[0][1],
                functional.correlator[1][0],
                functional.correlator[1][1],
            ),
            dtype=float,
        )
        start = perf_counter()
        value = self.problem.solve(
            solver=self.solver,
            warm_start=True,
            tol_gap_abs=self.solver_tolerance,
            tol_gap_rel=self.solver_tolerance,
            tol_feas=self.solver_tolerance,
            max_iter=1_000,
        )
        elapsed = perf_counter() - start
        if self.problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            raise RuntimeError(f"NPA solver failed with status {self.problem.status}")
        if value is None or not math.isfinite(float(value)):
            raise RuntimeError("NPA solver returned a non-finite objective")
        return float(value), self.problem.status, elapsed


def _solve_npa_upper_bound(
    program: _NPAQ1ABProgram,
    input_distribution: Matrix2x2,
    utility: ParityUtility2x2,
    efficiencies: tuple[float, float],
    solver_error_margin: float,
) -> NPAUpperBoundResult:
    evaluations: list[FallbackNPAEvaluation] = []
    for fallback_strategy in _fallback_strategies():
        functional = lossy_correlator_functional(
            input_distribution,
            utility,
            efficiencies,
            fallback_strategy,
        )
        raw_value, status, solve_time = program.solve(functional)
        guarded_value = min(
            functional.maximum_utility,
            raw_value + solver_error_margin,
        )
        evaluations.append(
            FallbackNPAEvaluation(
                fallback_strategy=fallback_strategy,
                raw_upper_bound=raw_value,
                guarded_upper_bound=guarded_value,
                solver_status=status,
                solve_time_s=solve_time,
            )
        )
    best = max(evaluations, key=lambda evaluation: evaluation.guarded_upper_bound)
    return NPAUpperBoundResult(
        efficiencies=efficiencies,
        upper_bound=best.guarded_upper_bound,
        raw_upper_bound=best.raw_upper_bound,
        fallback_strategy=best.fallback_strategy,
        solver_error_margin=solver_error_margin,
        relaxation="NPA_Q1+AB_real_moments",
        solver=program.solver,
        evaluations=tuple(evaluations),
    )


def lossy_npa_upper_bound(
    input_distribution: Matrix2x2,
    utility: ParityUtility2x2,
    efficiencies: tuple[float, float],
    *,
    solver: str = "CLARABEL",
    solver_tolerance: float = 1e-8,
    solver_error_margin: float = 1e-7,
) -> NPAUpperBoundResult:
    """Upper-bound a lossy value with the real NPA Q1+AB relaxation."""

    if not math.isfinite(solver_error_margin) or solver_error_margin < 0.0:
        raise ValueError("solver_error_margin must be finite and nonnegative")
    program = _NPAQ1ABProgram(solver, solver_tolerance)
    return _solve_npa_upper_bound(
        program,
        input_distribution,
        utility,
        efficiencies,
        solver_error_margin,
    )


def find_npa_threshold_lower_bound(
    input_distribution: Matrix2x2,
    utility: ParityUtility2x2,
    classical_value: float,
    *,
    lower_efficiency: float = 2.0 / 3.0,
    upper_efficiency: float = 1.0,
    efficiency_tolerance: float = 5e-4,
    advantage_tolerance: float = 2e-7,
    solver: str = "CLARABEL",
    solver_tolerance: float = 1e-8,
    solver_error_margin: float = 1e-7,
) -> NPAThresholdLowerBoundResult:
    """Find a numerical lower bound on eta-star from Q1+AB upper bounds."""

    _validate_probability(classical_value, "classical_value")
    _validate_probability(lower_efficiency, "lower_efficiency")
    _validate_probability(upper_efficiency, "upper_efficiency")
    if lower_efficiency >= upper_efficiency:
        raise ValueError("lower_efficiency must be less than upper_efficiency")
    if not math.isfinite(efficiency_tolerance) or efficiency_tolerance <= 0.0:
        raise ValueError("efficiency_tolerance must be finite and positive")
    if not math.isfinite(advantage_tolerance):
        raise ValueError("advantage_tolerance must be finite")
    if not math.isfinite(solver_error_margin) or solver_error_margin < 0.0:
        raise ValueError("solver_error_margin must be finite and nonnegative")
    if advantage_tolerance < solver_error_margin:
        raise ValueError(
            "advantage_tolerance must be at least the solver error margin"
        )
    program = _NPAQ1ABProgram(solver, solver_tolerance)
    evaluations: list[NPAThresholdEvaluation] = []

    def evaluate(efficiency: float) -> float:
        result = _solve_npa_upper_bound(
            program,
            input_distribution,
            utility,
            (efficiency, efficiency),
            solver_error_margin,
        )
        advantage_bound = result.upper_bound - classical_value
        evaluations.append(
            NPAThresholdEvaluation(
                efficiency=efficiency,
                quantum_upper_bound=result.upper_bound,
                advantage_upper_bound=advantage_bound,
                solver_statuses=tuple(
                    evaluation.solver_status for evaluation in result.evaluations
                ),
            )
        )
        return advantage_bound

    lower = lower_efficiency
    upper = upper_efficiency
    if evaluate(lower) > advantage_tolerance:
        raise ValueError(
            "Q1+AB cannot certify the configured lower efficiency as no-advantage"
        )
    if evaluate(upper) <= advantage_tolerance:
        return NPAThresholdLowerBoundResult(
            threshold_lower_bound=1.0,
            transition_upper_bound=1.0,
            classical_value=classical_value,
            efficiency_tolerance=efficiency_tolerance,
            advantage_tolerance=advantage_tolerance,
            solver_error_margin=solver_error_margin,
            evaluations=tuple(evaluations),
        )

    while upper - lower > efficiency_tolerance:
        midpoint = (lower + upper) / 2.0
        if evaluate(midpoint) <= advantage_tolerance:
            lower = midpoint
        else:
            upper = midpoint

    return NPAThresholdLowerBoundResult(
        threshold_lower_bound=lower,
        transition_upper_bound=upper,
        classical_value=classical_value,
        efficiency_tolerance=efficiency_tolerance,
        advantage_tolerance=advantage_tolerance,
        solver_error_margin=solver_error_margin,
        evaluations=tuple(evaluations),
    )
