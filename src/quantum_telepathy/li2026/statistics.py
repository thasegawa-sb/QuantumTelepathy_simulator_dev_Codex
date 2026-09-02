"""Finite-statistics certification for Li et al. Eqs. 16-18 and 40-43."""

from __future__ import annotations

import math
from collections.abc import Iterable
from numbers import Integral

import numpy as np
from scipy.stats import binom


class NoFiniteCertificationError(ValueError):
    """Raised when the quantum win probability does not exceed the classical one."""


class CertificationSearchLimitError(RuntimeError):
    """Raised when no certifying round count is found within the configured limit."""


def _validate_probability(name: str, value: float) -> float:
    probability = float(value)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError(f"{name} must be a finite value in [0, 1]")
    return probability


def _validate_positive_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def binomial_tail_p_value(
    wins: int,
    rounds: int,
    classical_win_probability: float,
) -> float:
    """Return Li Eq. 16, the classical probability of at least ``wins`` wins."""

    if isinstance(wins, bool) or not isinstance(wins, Integral):
        raise ValueError("wins must be an integer")
    if isinstance(rounds, bool) or not isinstance(rounds, Integral) or rounds < 0:
        raise ValueError("rounds must be a nonnegative integer")
    wins = int(wins)
    rounds = int(rounds)
    probability = _validate_probability(
        "classical_win_probability", classical_win_probability
    )
    if wins <= 0:
        return 1.0
    if wins > rounds:
        return 0.0
    return float(binom.sf(wins - 1, rounds, probability))


def expected_win_count(rounds: int, quantum_win_probability: float) -> int:
    """Return ceil(rounds * omega_Q) with integer-boundary stabilization."""

    if isinstance(rounds, bool) or not isinstance(rounds, Integral) or rounds < 0:
        raise ValueError("rounds must be a nonnegative integer")
    probability = _validate_probability(
        "quantum_win_probability", quantum_win_probability
    )
    product = int(rounds) * probability
    # Avoid a spurious extra win when multiplication lands one ULP above an integer.
    return int(math.ceil(math.nextafter(product, -math.inf)))


def certification_p_value(
    rounds: int,
    classical_win_probability: float,
    quantum_win_probability: float,
) -> float:
    """Return Li Eq. 40 at the ceiling of the expected quantum wins."""

    wins = expected_win_count(rounds, quantum_win_probability)
    return binomial_tail_p_value(wins, rounds, classical_win_probability)


def _first_certifying_round(
    classical_win_probability: float,
    quantum_win_probability: float,
    alpha: float,
    *,
    lower_bound: int,
    max_rounds: int,
    chunk_size: int,
) -> int:
    start = lower_bound
    while start <= max_rounds:
        stop = min(max_rounds + 1, start + chunk_size)
        rounds = np.arange(start, stop, dtype=np.int64)
        products = rounds * quantum_win_probability
        expected_wins = np.ceil(np.nextafter(products, -np.inf)).astype(np.int64)
        tails = binom.sf(
            expected_wins - 1,
            rounds,
            classical_win_probability,
        )
        if np.any(np.isnan(tails)):
            raise ArithmeticError("binomial survival function returned NaN")
        passing = np.flatnonzero(tails < alpha)
        if passing.size:
            return int(rounds[int(passing[0])])
        start = stop
    raise CertificationSearchLimitError(
        f"no certifying round count found at or below max_rounds={max_rounds}"
    )


def required_trials(
    classical_win_probability: float,
    quantum_win_probability: float,
    alpha: float,
    *,
    max_rounds: int = 100_000_000,
    chunk_size: int = 32_768,
) -> int:
    """Return the exact minimal positive round count in Li Eqs. 17 and 42."""

    classical = _validate_probability(
        "classical_win_probability", classical_win_probability
    )
    quantum = _validate_probability(
        "quantum_win_probability", quantum_win_probability
    )
    significance = _validate_probability("alpha", alpha)
    if significance in (0.0, 1.0):
        raise ValueError("alpha must be strictly between 0 and 1")
    if quantum <= classical:
        raise NoFiniteCertificationError(
            "quantum_win_probability must exceed classical_win_probability"
        )
    limit = _validate_positive_integer("max_rounds", max_rounds)
    chunk = _validate_positive_integer("chunk_size", chunk_size)
    return _first_certifying_round(
        classical,
        quantum,
        significance,
        lower_bound=1,
        max_rounds=limit,
        chunk_size=chunk,
    )


def required_trials_sequence(
    classical_win_probability: float,
    quantum_win_probabilities: Iterable[float],
    alpha: float,
    *,
    max_rounds: int = 100_000_000,
    chunk_size: int = 32_768,
) -> tuple[int, ...]:
    """Evaluate ``n_req`` efficiently for a nonincreasing sequence of omega_Q.

    If the quantum win probability decreases, the p-value at every fixed round
    count cannot decrease. The previous required count is therefore a valid
    lower bound for the next exact search.
    """

    classical = _validate_probability(
        "classical_win_probability", classical_win_probability
    )
    significance = _validate_probability("alpha", alpha)
    if significance in (0.0, 1.0):
        raise ValueError("alpha must be strictly between 0 and 1")
    limit = _validate_positive_integer("max_rounds", max_rounds)
    chunk = _validate_positive_integer("chunk_size", chunk_size)
    probabilities = tuple(
        _validate_probability("quantum_win_probability", value)
        for value in quantum_win_probabilities
    )

    previous_probability = math.inf
    lower_bound = 1
    results: list[int] = []
    for probability in probabilities:
        if probability > previous_probability:
            raise ValueError("quantum_win_probabilities must be nonincreasing")
        if probability <= classical:
            raise NoFiniteCertificationError(
                "every quantum win probability must exceed the classical one"
            )
        required = _first_certifying_round(
            classical,
            probability,
            significance,
            lower_bound=lower_bound,
            max_rounds=limit,
            chunk_size=chunk,
        )
        results.append(required)
        previous_probability = probability
        lower_bound = required
    return tuple(results)


def required_trial_rate(required_round_count: int, t_env: float) -> float:
    """Return Li Eqs. 18 and 41, ``R_req = n_req / T_env`` in inverse seconds."""

    rounds = _validate_positive_integer("required_round_count", required_round_count)
    duration = float(t_env)
    if not math.isfinite(duration) or duration <= 0.0:
        raise ValueError("t_env must be a finite positive duration")
    return rounds / duration


def required_rate(
    classical_win_probability: float,
    quantum_win_probability: float,
    alpha: float,
    t_env: float,
    *,
    max_rounds: int = 100_000_000,
    chunk_size: int = 32_768,
) -> float:
    """Return the required trial rate after evaluating the exact ``n_req``."""

    rounds = required_trials(
        classical_win_probability,
        quantum_win_probability,
        alpha,
        max_rounds=max_rounds,
        chunk_size=chunk_size,
    )
    return required_trial_rate(rounds, t_env)
