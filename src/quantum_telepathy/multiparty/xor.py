"""Generic binary-input/output multiparty XOR-game calculations."""

from __future__ import annotations

import cmath
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from numbers import Integral

import numpy as np
from scipy.optimize import differential_evolution

InputTuple = tuple[int, ...]
InputDistribution = Mapping[InputTuple, float]
ParityUtility = Callable[[int, InputTuple], float]
XORCoefficients = Mapping[InputTuple, float]


def _party_count(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError("party_count must be a positive integer")
    return int(value)


def binary_input_tuples(party_count: int) -> tuple[InputTuple, ...]:
    """Return all binary input tuples in lexicographic order."""

    count = _party_count(party_count)
    return tuple(product((0, 1), repeat=count))


def validate_binary_input_distribution(
    distribution: InputDistribution,
    *,
    tolerance: float = 1e-12,
) -> int:
    """Validate a complete binary-input probability distribution."""

    if not distribution:
        raise ValueError("input distribution must be nonempty")
    lengths = {len(inputs) for inputs in distribution}
    if len(lengths) != 1:
        raise ValueError("all input tuples must have the same arity")
    party_count = _party_count(next(iter(lengths)))
    expected = set(binary_input_tuples(party_count))
    if set(distribution) != expected:
        raise ValueError("input distribution must contain every binary input tuple")
    probabilities = tuple(float(distribution[inputs]) for inputs in expected)
    if any(not math.isfinite(value) or value < 0.0 for value in probabilities):
        raise ValueError("input probabilities must be finite and nonnegative")
    total = sum(probabilities)
    if abs(total - 1.0) > tolerance:
        raise ValueError(f"input probabilities sum to {total}, not 1")
    return party_count


def independent_bernoulli_distribution(
    party_count: int,
    probability_one: float,
) -> dict[InputTuple, float]:
    """Return IID Bernoulli binary inputs for an arbitrary party count."""

    count = _party_count(party_count)
    probability = float(probability_one)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError("probability_one must be a finite value in [0, 1]")
    return {
        inputs: probability ** sum(inputs)
        * (1.0 - probability) ** (count - sum(inputs))
        for inputs in binary_input_tuples(count)
    }


def xor_coefficients(
    distribution: InputDistribution,
    utility: ParityUtility,
) -> dict[InputTuple, float]:
    """Return ``M_x = P(x) sum_o (-1)^o u(o|x)`` from Li Eq. B14."""

    validate_binary_input_distribution(distribution)
    coefficients: dict[InputTuple, float] = {}
    for inputs, probability in distribution.items():
        utility_zero = float(utility(0, inputs))
        utility_one = float(utility(1, inputs))
        if not math.isfinite(utility_zero) or not math.isfinite(utility_one):
            raise ValueError("utility values must be finite")
        coefficients[inputs] = float(probability) * (utility_zero - utility_one)
    return coefficients


def _validate_coefficients(coefficients: XORCoefficients) -> int:
    if not coefficients:
        raise ValueError("XOR coefficients must be nonempty")
    lengths = {len(inputs) for inputs in coefficients}
    if len(lengths) != 1:
        raise ValueError("all coefficient input tuples must have the same arity")
    party_count = _party_count(next(iter(lengths)))
    if set(coefficients) != set(binary_input_tuples(party_count)):
        raise ValueError("XOR coefficients must contain every binary input tuple")
    if any(not math.isfinite(float(value)) for value in coefficients.values()):
        raise ValueError("XOR coefficients must be finite")
    return party_count


@dataclass(frozen=True)
class MultipartyClassicalBiasResult:
    """Maximum XOR bias over all deterministic local sign strategies."""

    bias: float
    local_signs: tuple[tuple[int, int], ...]
    strategy_count: int


def deterministic_classical_bias(
    coefficients: XORCoefficients,
) -> MultipartyClassicalBiasResult:
    """Enumerate all ``4^k`` deterministic local binary strategies."""

    party_count = _validate_coefficients(coefficients)
    local_sign_options = tuple(product((-1, 1), repeat=2))
    best_bias = float("-inf")
    best_signs: tuple[tuple[int, int], ...] | None = None
    strategy_count = 0
    for local_signs in product(local_sign_options, repeat=party_count):
        strategy_count += 1
        bias = sum(
            float(coefficient)
            * math.prod(local_signs[index][inputs[index]] for index in range(party_count))
            for inputs, coefficient in coefficients.items()
        )
        if bias > best_bias:
            best_bias = bias
            best_signs = local_signs
    if best_signs is None:
        raise ArithmeticError("no deterministic local strategies were generated")
    return MultipartyClassicalBiasResult(best_bias, best_signs, strategy_count)


def _complex_ghz_polynomial(
    coefficients: XORCoefficients,
    phase_steps: Sequence[float],
) -> complex:
    party_count = _validate_coefficients(coefficients)
    if len(phase_steps) != party_count:
        raise ValueError("one phase step is required per party")
    phases = tuple(float(value) for value in phase_steps)
    if any(not math.isfinite(value) for value in phases):
        raise ValueError("phase steps must be finite")
    return sum(
        float(coefficient)
        * cmath.exp(
            1j * sum(phases[index] * inputs[index] for index in range(party_count))
        )
        for inputs, coefficient in coefficients.items()
    )


def ghz_bias_at_phases(
    coefficients: XORCoefficients,
    phase_offset: float,
    phase_steps: Sequence[float],
) -> float:
    """Evaluate the equatorial GHZ bias in Li Eqs. B10-B15."""

    offset = float(phase_offset)
    if not math.isfinite(offset):
        raise ValueError("phase_offset must be finite")
    value = cmath.exp(1j * offset) * _complex_ghz_polynomial(
        coefficients, phase_steps
    )
    return float(value.real)


@dataclass(frozen=True)
class GHZOptimizationResult:
    """Optimized GHZ-equatorial XOR bias and measurement phases."""

    bias: float
    phase_offset: float
    phase_steps: tuple[float, ...]
    method: str


def optimize_ghz_equatorial_bias(
    coefficients: XORCoefficients,
    *,
    seed: int = 0,
    tolerance: float = 1e-11,
) -> GHZOptimizationResult:
    """Numerically optimize arbitrary multiparty GHZ equatorial phases.

    The global phase offset is eliminated analytically, leaving the modulus of
    a complex multilinear polynomial. Differential evolution is retained as a
    general numerical cross-check, not as a formal global certificate.
    """

    party_count = _validate_coefficients(coefficients)
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be finite and positive")

    def objective(phases: np.ndarray) -> float:
        return -abs(_complex_ghz_polynomial(coefficients, phases))

    optimization = differential_evolution(
        objective,
        bounds=[(-math.pi, math.pi)] * party_count,
        seed=seed,
        tol=tolerance,
        polish=True,
        workers=1,
        updating="immediate",
    )
    phases = tuple(float(value) for value in optimization.x)
    polynomial = _complex_ghz_polynomial(coefficients, phases)
    offset = -cmath.phase(polynomial) if polynomial != 0.0 else 0.0
    return GHZOptimizationResult(
        bias=abs(polynomial),
        phase_offset=offset,
        phase_steps=phases,
        method="differential_evolution",
    )


def _symmetric_weight_coefficients(
    coefficients: XORCoefficients,
    *,
    tolerance: float,
) -> tuple[float, ...]:
    party_count = _validate_coefficients(coefficients)
    by_weight: dict[int, list[float]] = {
        weight: [] for weight in range(party_count + 1)
    }
    for inputs, coefficient in coefficients.items():
        by_weight[sum(inputs)].append(float(coefficient))
    aggregated: list[float] = []
    for weight in range(party_count + 1):
        values = by_weight[weight]
        if max(values) - min(values) > tolerance:
            raise ValueError("coefficients are not permutation-symmetric")
        aggregated.append(sum(values))
    return tuple(aggregated)


def symmetric_ghz_equatorial_bias(
    coefficients: XORCoefficients,
    *,
    symmetry_tolerance: float = 1e-12,
) -> GHZOptimizationResult:
    """Optimize a permutation-symmetric GHZ XOR polynomial on its diagonal.

    A symmetric multi-affine polynomial reaches its maximum modulus on the unit
    polydisc at a diagonal point. Stationary phases are obtained from the roots
    of the derivative of the resulting trigonometric polynomial; a dense
    fallback guards numerical root filtering.
    """

    party_count = _validate_coefficients(coefficients)
    if not math.isfinite(symmetry_tolerance) or symmetry_tolerance < 0.0:
        raise ValueError("symmetry_tolerance must be finite and nonnegative")
    polynomial = _symmetric_weight_coefficients(
        coefficients, tolerance=symmetry_tolerance
    )
    degree = party_count

    autocorrelation = [
        sum(
            polynomial[index + lag] * polynomial[index]
            for index in range(degree + 1 - lag)
        )
        for lag in range(degree + 1)
    ]
    derivative = np.zeros(2 * degree + 1, dtype=np.float64)
    for lag in range(1, degree + 1):
        derivative[degree + lag] += lag * autocorrelation[lag]
        derivative[degree - lag] -= lag * autocorrelation[lag]

    candidate_phases = {0.0, math.pi}
    nonzero = np.flatnonzero(abs(derivative) > 1e-15)
    if nonzero.size:
        first = int(nonzero[0])
        last = int(nonzero[-1])
        roots = np.roots(derivative[first : last + 1][::-1])
        for root in roots:
            if abs(abs(root) - 1.0) <= 1e-7:
                candidate_phases.add(float(cmath.phase(root) % (2.0 * math.pi)))

    dense_phases = np.linspace(0.0, 2.0 * math.pi, 2048, endpoint=False)
    dense_values = np.abs(
        sum(
            coefficient * np.exp(1j * power * dense_phases)
            for power, coefficient in enumerate(polynomial)
        )
    )
    candidate_phases.add(float(dense_phases[int(np.argmax(dense_values))]))

    def diagonal_value(phase: float) -> complex:
        return sum(
            coefficient * cmath.exp(1j * power * phase)
            for power, coefficient in enumerate(polynomial)
        )

    ranked = sorted(
        (
            (abs(diagonal_value(phase)), phase, diagonal_value(phase))
            for phase in candidate_phases
        ),
        key=lambda item: (-item[0], item[1]),
    )
    bias, phase, complex_value = ranked[0]
    offset = -cmath.phase(complex_value) if complex_value != 0.0 else 0.0
    return GHZOptimizationResult(
        bias=float(bias),
        phase_offset=float(offset),
        phase_steps=(float(phase),) * party_count,
        method="symmetric_stationary_polynomial",
    )
