import math

import pytest

from quantum_telepathy.core.classical import maximize_classical_value
from quantum_telepathy.core.xor_game import (
    chsh_matrix,
    chsh_values,
    classical_bias,
    classical_value,
    quantum_bias_2x2,
    quantum_value,
)
from quantum_telepathy.li2026.fidelity import fidelity_threshold, noisy_gap


def test_chsh_values_match_analytical_oracle():
    values = chsh_values()

    assert values.classical_bias == pytest.approx(0.5, abs=1e-12)
    assert values.quantum_bias == pytest.approx(1.0 / math.sqrt(2.0), abs=1e-12)
    assert values.classical_value == pytest.approx(0.75, abs=1e-12)
    assert values.quantum_value == pytest.approx(
        (1.0 + 1.0 / math.sqrt(2.0)) / 2.0,
        abs=1e-12,
    )
    assert values.gap == pytest.approx((math.sqrt(2.0) - 1.0) / 4.0, abs=1e-12)


def test_chsh_value_functions_are_consistent():
    matrix = chsh_matrix()

    assert classical_bias(matrix) == pytest.approx(0.5, abs=1e-12)
    assert quantum_bias_2x2(matrix) == pytest.approx(1.0 / math.sqrt(2.0), abs=1e-12)
    assert classical_value(matrix) == pytest.approx(0.75, abs=1e-12)
    assert quantum_value(matrix) == pytest.approx(
        (1.0 + 1.0 / math.sqrt(2.0)) / 2.0,
        abs=1e-12,
    )


def test_generic_deterministic_enumeration_recovers_chsh_classical_value():
    input_distribution = {
        (0, 0): 0.25,
        (0, 1): 0.25,
        (1, 0): 0.25,
        (1, 1): 0.25,
    }

    def utility(observation, decision):
        x, y = observation
        a, b = decision
        return 1.0 if (a ^ b) == (x & y) else 0.0

    result = maximize_classical_value(
        observation_sets=((0, 1), (0, 1)),
        decision_sets=((0, 1), (0, 1)),
        input_distribution=input_distribution,
        utility=utility,
    )

    assert result.strategy_count == 16
    assert result.value == pytest.approx(0.75, abs=1e-12)


def test_chsh_fidelity_threshold_oracle():
    values = chsh_values()
    epsilon_th = fidelity_threshold(values.classical_bias, values.quantum_bias)

    assert epsilon_th == pytest.approx(1.0 - 1.0 / math.sqrt(2.0), abs=1e-12)
    assert noisy_gap(epsilon_th, values.classical_bias, values.quantum_bias) == pytest.approx(
        0.0,
        abs=1e-12,
    )
