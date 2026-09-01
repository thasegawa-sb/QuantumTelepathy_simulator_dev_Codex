import pytest

from quantum_telepathy.ding_jiang.fig3 import evaluate_fig3_point
from quantum_telepathy.ding_jiang.hft import biased_chsh_values


@pytest.mark.parametrize(
    ("p", "beta"),
    [(0.0, 0.0), (0.2, 0.4), (0.37, 0.18), (0.5, 0.5), (0.81, 0.7), (1.0, 1.0)],
)
def test_fig3_classical_value_matches_independent_deterministic_enumeration(p, beta):
    point = evaluate_fig3_point(p, beta)

    assert point.classical_oracle_abs_error <= 1e-12
    assert point.deterministic_strategy_count == 16


@pytest.mark.parametrize("p", [index / 20.0 for index in range(21)])
def test_fig3_has_zero_gap_at_beta_half(p):
    point = evaluate_fig3_point(p, beta=0.5)

    assert point.gap == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("p", [index / 20.0 for index in range(21)])
@pytest.mark.parametrize("beta", [0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
def test_fig3_gap_is_symmetric_under_beta_relabeling(p, beta):
    point = evaluate_fig3_point(p, beta)
    mirror = evaluate_fig3_point(p, 1.0 - beta)

    assert point.gap == pytest.approx(mirror.gap, abs=1e-12)


@pytest.mark.parametrize("p", [index / 100.0 for index in range(101)])
def test_fig3_beta_zero_cross_section_matches_theorem_10(p):
    point = evaluate_fig3_point(p, beta=0.0)
    theorem = biased_chsh_values(p)

    assert point.classical_value == pytest.approx(theorem.classical_value, abs=1e-10)
    assert point.quantum_value == pytest.approx(theorem.quantum_value, abs=1e-10)
    assert point.gap == pytest.approx(theorem.gap, abs=1e-10)


def test_fig3_global_peak_contains_chsh_point():
    point = evaluate_fig3_point(p=0.5, beta=0.0)

    assert point.gap == pytest.approx(0.10355339059327379, abs=1e-12)
