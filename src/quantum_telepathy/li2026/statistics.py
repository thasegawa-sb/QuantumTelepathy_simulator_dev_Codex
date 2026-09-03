"""Finite-statistics certification for Li et al. Eqs. 16-21 and 40-43."""

from __future__ import annotations

import math
from collections.abc import Iterable
from numbers import Integral

import numpy as np
from scipy.stats import binom


_INITIAL_SEARCH_CHUNK_SIZE = 256


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


def _validate_score_range(score_min: float, score_max: float) -> tuple[float, float]:
    minimum = float(score_min)
    maximum = float(score_max)
    if not math.isfinite(minimum) or not math.isfinite(maximum):
        raise ValueError("score bounds must be finite")
    if maximum <= minimum:
        raise ValueError("score_max must be greater than score_min")
    return minimum, maximum


def _validate_expected_score(
    name: str,
    value: float,
    score_min: float,
    score_max: float,
) -> float:
    score = float(value)
    if not math.isfinite(score) or not score_min <= score <= score_max:
        raise ValueError(f"{name} must be a finite value in [score_min, score_max]")
    return score


def expected_score_threshold(rounds: int, quantum_expected_score: float) -> int:
    """Return Li Sec. II C's ``ceil(m * omega_Q)`` score threshold."""

    if isinstance(rounds, bool) or not isinstance(rounds, Integral) or rounds < 0:
        raise ValueError("rounds must be a nonnegative integer")
    score = float(quantum_expected_score)
    if not math.isfinite(score):
        raise ValueError("quantum_expected_score must be finite")
    product = int(rounds) * score
    return int(math.ceil(math.nextafter(product, -math.inf)))


def _weighted_log_tail(log_tail: float, weight: float) -> float:
    if weight == 0.0:
        return 0.0
    return weight * log_tail


def score_p_value_bound(
    total_score: float,
    rounds: int,
    classical_expected_score: float,
    score_min: float,
    score_max: float,
) -> float:
    """Return the Li Eq. 20 upper bound for a general bounded score.

    The two binomial upper tails are evaluated in log space and geometrically
    interpolated at the normalized score ``mu``. The result is capped at one,
    as required for a usable p-value upper bound.
    """

    if isinstance(rounds, bool) or not isinstance(rounds, Integral) or rounds <= 0:
        raise ValueError("rounds must be a positive integer")
    rounds = int(rounds)
    minimum, maximum = _validate_score_range(score_min, score_max)
    classical = _validate_expected_score(
        "classical_expected_score",
        classical_expected_score,
        minimum,
        maximum,
    )
    score = float(total_score)
    if not math.isfinite(score):
        raise ValueError("total_score must be finite")

    minimum_total = rounds * minimum
    maximum_total = rounds * maximum
    if score <= minimum_total:
        return 1.0
    if score > maximum_total:
        return 0.0

    score_range = maximum - minimum
    mu = (score - minimum_total) / score_range
    xi = (classical - minimum) / score_range
    lower = math.floor(mu)
    upper = math.ceil(mu)
    fraction = mu - lower
    lower_log_tail = float(binom.logsf(lower - 1, rounds, xi))
    upper_log_tail = (
        float(binom.logsf(upper - 1, rounds, xi)) if fraction != 0.0 else 0.0
    )
    log_bound = (
        1.0
        + _weighted_log_tail(lower_log_tail, 1.0 - fraction)
        + _weighted_log_tail(upper_log_tail, fraction)
    )
    if math.isnan(log_bound):
        raise ArithmeticError("general-score p-value bound returned NaN")
    return min(1.0, math.exp(log_bound))


def score_certification_p_value(
    rounds: int,
    classical_expected_score: float,
    quantum_expected_score: float,
    score_min: float,
    score_max: float,
) -> float:
    """Evaluate Eq. 20 at ``c = ceil(m * omega_Q)`` from Li Sec. II C."""

    minimum, maximum = _validate_score_range(score_min, score_max)
    quantum = _validate_expected_score(
        "quantum_expected_score",
        quantum_expected_score,
        minimum,
        maximum,
    )
    threshold = expected_score_threshold(rounds, quantum)
    return score_p_value_bound(
        threshold,
        rounds,
        classical_expected_score,
        minimum,
        maximum,
    )


def required_score_trials(
    classical_expected_score: float,
    quantum_expected_score: float,
    alpha: float,
    score_min: float,
    score_max: float,
    *,
    max_rounds: int = 100_000_000,
    chunk_size: int = 32_768,
) -> int:
    """Return the exact minimal round count certified by Li Eqs. 20-21."""

    minimum, maximum = _validate_score_range(score_min, score_max)
    classical = _validate_expected_score(
        "classical_expected_score",
        classical_expected_score,
        minimum,
        maximum,
    )
    quantum = _validate_expected_score(
        "quantum_expected_score",
        quantum_expected_score,
        minimum,
        maximum,
    )
    significance = _validate_probability("alpha", alpha)
    if significance in (0.0, 1.0):
        raise ValueError("alpha must be strictly between 0 and 1")
    if quantum <= classical:
        raise NoFiniteCertificationError(
            "quantum_expected_score must exceed classical_expected_score"
        )
    limit = _validate_positive_integer("max_rounds", max_rounds)
    chunk = _validate_positive_integer("chunk_size", chunk_size)

    score_range = maximum - minimum
    xi = (classical - minimum) / score_range
    log_alpha = math.log(significance)
    start = 1
    block_size = min(chunk, _INITIAL_SEARCH_CHUNK_SIZE)
    while start <= limit:
        stop = min(limit + 1, start + block_size)
        rounds = np.arange(start, stop, dtype=np.int64)
        expected_totals = np.nextafter(rounds * quantum, -np.inf)
        thresholds = np.ceil(expected_totals)
        mu = (thresholds - rounds * minimum) / score_range
        lower = np.floor(mu).astype(np.int64)
        upper = np.ceil(mu).astype(np.int64)
        fractions = mu - lower
        lower_log_tails = binom.logsf(lower - 1, rounds, xi)
        lower_terms = np.zeros_like(fractions)
        upper_terms = np.zeros_like(fractions)
        np.multiply(
            1.0 - fractions,
            lower_log_tails,
            out=lower_terms,
            where=fractions != 1.0,
        )
        interpolated = fractions != 0.0
        if np.any(interpolated):
            upper_log_tails = binom.logsf(
                upper[interpolated] - 1,
                rounds[interpolated],
                xi,
            )
            upper_terms[interpolated] = (
                fractions[interpolated] * upper_log_tails
            )
        log_bounds = 1.0 + lower_terms + upper_terms
        if np.any(np.isnan(log_bounds)):
            raise ArithmeticError("general-score p-value bound returned NaN")
        passing = np.flatnonzero(log_bounds < log_alpha)
        if passing.size:
            return int(rounds[int(passing[0])])
        start = stop
        block_size = min(chunk, 2 * block_size)
    raise CertificationSearchLimitError(
        f"no certifying round count found at or below max_rounds={limit}"
    )


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
    block_size = min(chunk_size, _INITIAL_SEARCH_CHUNK_SIZE)
    while start <= max_rounds:
        stop = min(max_rounds + 1, start + block_size)
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
        block_size = min(chunk_size, 2 * block_size)
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
