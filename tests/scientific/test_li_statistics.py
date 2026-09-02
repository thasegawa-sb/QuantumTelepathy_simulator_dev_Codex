import math
from decimal import Decimal, getcontext

import pytest

from quantum_telepathy.li2026.statistics import (
    CertificationSearchLimitError,
    NoFiniteCertificationError,
    binomial_tail_p_value,
    certification_p_value,
    expected_win_count,
    required_rate,
    required_trial_rate,
    required_trials,
    required_trials_sequence,
)


getcontext().prec = 60


def _direct_decimal_tail(wins, rounds, probability):
    probability = Decimal(str(probability))
    return sum(
        Decimal(math.comb(rounds, count))
        * probability**count
        * (Decimal(1) - probability) ** (rounds - count)
        for count in range(wins, rounds + 1)
    )


def _brute_force_required_trials(classical, quantum, alpha, limit=1000):
    for rounds in range(1, limit + 1):
        wins = math.ceil(rounds * quantum)
        if _direct_decimal_tail(wins, rounds, classical) < Decimal(str(alpha)):
            return rounds
    raise AssertionError("brute-force test limit was insufficient")


@pytest.mark.parametrize(
    ("wins", "rounds", "probability"),
    [(3, 5, 0.5), (7, 10, 0.75), (19, 25, 0.63), (30, 34, 0.75)],
)
def test_binomial_tail_matches_independent_decimal_direct_sum(
    wins, rounds, probability
):
    expected = float(_direct_decimal_tail(wins, rounds, probability))

    assert binomial_tail_p_value(wins, rounds, probability) == pytest.approx(
        expected, rel=1e-13, abs=1e-15
    )


def test_binomial_tail_handles_support_boundaries():
    assert binomial_tail_p_value(0, 10, 0.75) == 1.0
    assert binomial_tail_p_value(11, 10, 0.75) == 0.0
    assert binomial_tail_p_value(1, 0, 0.75) == 0.0


@pytest.mark.parametrize(
    ("rounds", "probability", "expected"),
    [
        (10, 0.8, 8),
        (3, 1.0 / 3.0, 1),
        (34, (1.0 + 1.0 / math.sqrt(2.0)) / 2.0, 30),
    ],
)
def test_expected_win_count_stabilizes_integer_boundaries(
    rounds, probability, expected
):
    assert expected_win_count(rounds, probability) == expected


@pytest.mark.parametrize(
    ("epsilon", "alpha", "expected_rounds"),
    [(0.0, 0.05, 34), (0.0, 0.001, 143), (0.061, 0.05, 65), (0.061, 0.001, 238)],
)
def test_chsh_required_trials_match_independent_decimal_exhaustive_oracles(
    epsilon, alpha, expected_rounds
):
    classical = 0.75
    quantum = (1.0 + (1.0 - epsilon) / math.sqrt(2.0)) / 2.0

    actual = required_trials(classical, quantum, alpha)

    assert actual == expected_rounds
    assert actual == _brute_force_required_trials(classical, quantum, alpha)
    assert certification_p_value(actual, classical, quantum) < alpha


def test_required_trials_uses_strict_significance_inequality():
    classical = 0.5
    quantum = 0.75
    first = required_trials(classical, quantum, 0.2)
    boundary_alpha = certification_p_value(first, classical, quantum)

    assert required_trials(classical, quantum, boundary_alpha) > first


def test_required_trials_sequence_matches_individual_searches_and_is_monotone():
    classical = 0.75
    quantum = tuple(
        (1.0 + (1.0 - epsilon) / math.sqrt(2.0)) / 2.0
        for epsilon in (0.0, 0.061, 0.1, 0.2)
    )

    sequence = required_trials_sequence(classical, quantum, 0.05)
    individual = tuple(required_trials(classical, value, 0.05) for value in quantum)

    assert sequence == individual
    assert sequence == tuple(sorted(sequence))


def test_large_binomial_tail_remains_nonzero_without_direct_power_underflow():
    value = binomial_tail_p_value(900, 1000, 0.5)

    assert 0.0 < value < 1e-150


def test_required_rate_uses_stationary_window_in_seconds():
    assert required_trial_rate(238, 0.1) == pytest.approx(2380.0, abs=1e-12)
    quantum = (1.0 + (1.0 - 0.061) / math.sqrt(2.0)) / 2.0
    assert required_rate(0.75, quantum, 0.001, 0.1) == pytest.approx(
        2380.0,
        abs=1e-12,
    )


@pytest.mark.parametrize("quantum", [0.7, 0.75])
def test_required_trials_rejects_nonadvantageous_probabilities(quantum):
    with pytest.raises(NoFiniteCertificationError):
        required_trials(0.75, quantum, 0.05)


def test_required_trials_reports_search_limit_separately():
    with pytest.raises(CertificationSearchLimitError):
        required_trials(0.75, 0.751, 0.001, max_rounds=10, chunk_size=4)


def test_required_trials_sequence_requires_nonincreasing_quantum_values():
    with pytest.raises(ValueError, match="nonincreasing"):
        required_trials_sequence(0.5, (0.6, 0.7), 0.05)


@pytest.mark.parametrize(
    ("function", "arguments"),
    [
        (binomial_tail_p_value, (1, -1, 0.5)),
        (binomial_tail_p_value, (1, 2, -0.1)),
        (required_trials, (0.5, 0.6, 0.0)),
        (required_trials, (0.5, 0.6, 1.0)),
        (required_trial_rate, (1, 0.0)),
    ],
)
def test_statistics_reject_invalid_parameters(function, arguments):
    with pytest.raises(ValueError):
        function(*arguments)
