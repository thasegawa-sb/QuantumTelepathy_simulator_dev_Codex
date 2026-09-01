import math
from pathlib import Path

import pytest

from experiments.ding_jiang.reproduce_noise_robustness import reproduce
from quantum_telepathy.core.nonlocal_game import expected_utility
from quantum_telepathy.core.xor_game import independent_bernoulli_distribution
from quantum_telepathy.ding_jiang.hft import hedging_utility, ideal_hedging_values
from quantum_telepathy.ding_jiang.noise import (
    depolarize_qubit_behavior,
    depolarizing_robustness,
    noisy_hedging_gap,
    noisy_hedging_quantum_value,
)

BINARY_DECISIONS = ((0, 0), (0, 1), (1, 0), (1, 1))


def _behavior():
    conditional = {(0, 0): 0.6, (0, 1): 0.1, (1, 0): 0.2, (1, 1): 0.1}
    return {(x, y): dict(conditional) for x in range(2) for y in range(2)}


def _utility_function(beta):
    table = hedging_utility(beta)
    return lambda observation, decision: table[observation[0]][observation[1]][
        decision[0] ^ decision[1]
    ]


def test_eq_4_2_depolarizes_each_binary_output_toward_one_quarter():
    noisy = depolarize_qubit_behavior(_behavior(), nu=0.2)

    assert noisy[(0, 0)][(0, 0)] == pytest.approx(0.53, abs=1e-12)
    assert noisy[(0, 0)][(0, 1)] == pytest.approx(0.13, abs=1e-12)
    assert sum(noisy[(1, 1)].values()) == pytest.approx(1.0, abs=1e-12)


def test_eq_4_2_at_full_noise_is_uniform_behavior():
    noisy = depolarize_qubit_behavior(_behavior(), nu=1.0)

    assert all(
        noisy[observation][decision] == pytest.approx(0.25, abs=1e-12)
        for observation in noisy
        for decision in BINARY_DECISIONS
    )


@pytest.mark.parametrize(("p", "beta"), [(0.1, 0.0), (0.37, 0.2), (0.5, 0.5), (0.9, 1.0)])
def test_eq_4_3_matches_direct_behavior_mixture(p, beta):
    distribution_array = independent_bernoulli_distribution(p)
    distribution = {(x, y): distribution_array[x][y] for x in range(2) for y in range(2)}
    behavior = _behavior()
    noiseless = expected_utility(distribution, behavior, _utility_function(beta))
    noisy_behavior = depolarize_qubit_behavior(behavior, nu=0.17)
    direct = expected_utility(distribution, noisy_behavior, _utility_function(beta))

    assert direct == pytest.approx((1.0 - 0.17) * noiseless + 0.17 / 2.0, abs=1e-12)


def test_chsh_robustness_matches_closed_form_and_paper_maximum():
    values = ideal_hedging_values(p=0.5, beta=0.0)
    actual = depolarizing_robustness(values.classical_value, values.quantum_value)

    assert actual == pytest.approx(1.0 - 1.0 / math.sqrt(2.0), abs=1e-12)
    assert actual == pytest.approx(0.3, abs=0.01)


@pytest.mark.parametrize("nu", [0.01, 0.05, 0.1])
def test_chsh_noisy_gap_matches_independent_closed_form(nu):
    values = ideal_hedging_values(p=0.5, beta=0.0)
    expected = (1.0 - nu) * (1.0 + 1.0 / math.sqrt(2.0)) / 2.0 + nu / 2.0 - 0.75

    assert noisy_hedging_gap(0.75, values.quantum_value, nu) == pytest.approx(expected, abs=1e-12)


def test_robustness_is_exact_noise_threshold():
    values = ideal_hedging_values(p=0.5, beta=0.4)
    threshold = depolarizing_robustness(values.classical_value, values.quantum_value)

    assert threshold == pytest.approx(0.01941932430907969, abs=1e-12)
    assert noisy_hedging_gap(
        values.classical_value,
        values.quantum_value,
        threshold,
    ) == pytest.approx(0.0, abs=1e-12)
    assert (
        noisy_hedging_gap(
            values.classical_value,
            values.quantum_value,
            threshold / 2.0,
        )
        > 0.0
    )


def test_no_advantage_has_zero_robustness():
    values = ideal_hedging_values(p=0.5, beta=0.5)

    assert depolarizing_robustness(values.classical_value, values.quantum_value) == 0.0


@pytest.mark.parametrize("nu", [-0.01, 1.01, float("nan")])
def test_noise_functions_reject_invalid_nu(nu):
    with pytest.raises(ValueError):
        noisy_hedging_quantum_value(0.8, nu)


def test_depolarize_rejects_incomplete_behavior():
    with pytest.raises(ValueError, match="all four"):
        depolarize_qubit_behavior({(0, 0): {(0, 0): 1.0}}, nu=0.1)


def test_reproduction_experiment_passes_analytical_oracles(tmp_path):
    repository_root = Path(__file__).resolve().parents[2]
    config = (
        repository_root
        / "experiments"
        / "ding_jiang"
        / "configs"
        / "noise_robustness_v3.json"
    )

    summary = reproduce(config, tmp_path, render_plots=False)

    assert summary["overall_status"] == "PASS"
    assert summary["grid"] == {
        "p_count": 101,
        "beta_count": 101,
        "robustness_point_count": 10201,
        "noisy_gap_point_count": 30603,
    }
    assert all(value["status"] == "PASS" for value in summary["validations"].values())
    counts = list(summary["simulator_extrema"]["positive_point_count_by_nu"].values())
    assert counts == sorted(counts, reverse=True)
