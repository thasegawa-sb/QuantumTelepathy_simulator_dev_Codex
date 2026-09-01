from decimal import Decimal, getcontext
from pathlib import Path

import pytest

from experiments.ding_jiang.reproduce_type_ii_memory import reproduce
from quantum_telepathy.ding_jiang.memory import (
    TypeIIMemoryParameters,
    heralded_success_probability,
    minimum_memory_count_for_rate,
    per_arm_fiber_transmission,
    traversal_attempt_time_s,
    type_ii_memory_rate,
)

PAPER_PARAMETERS = TypeIIMemoryParameters(
    separation_km=56.3,
    fiber_speed_m_s=2e8,
    herald_speed_m_s=3e8,
    attenuation_db_per_km=0.17,
    projection_success_probability=0.5,
    collection_efficiency=0.5,
    detector_efficiency=0.9,
)


def _decimal_oracle() -> tuple[Decimal, Decimal, Decimal]:
    getcontext().prec = 50
    distance_m = Decimal("56300")
    distance_km = Decimal("56.3")
    attempt_time = distance_m / (2 * Decimal("2e8")) + distance_m / (
        2 * Decimal("3e8")
    )
    arm_transmission = Decimal(10) ** (
        -Decimal("0.1") * Decimal("0.17") * distance_km / 2
    )
    success_probability = (
        Decimal("0.5") * Decimal("0.5") * Decimal("0.9") * arm_transmission**2
    )
    return attempt_time, success_probability, success_probability / attempt_time


def test_v3_attempt_time_matches_independent_decimal_oracle():
    expected, _, _ = _decimal_oracle()

    actual = traversal_attempt_time_s(56.3, 2e8, 3e8)

    assert actual == pytest.approx(float(expected), abs=1e-15)
    assert actual * 1e6 == pytest.approx(230.0, abs=5.0)


def test_v3_success_probability_uses_both_half_distance_arms():
    arm = per_arm_fiber_transmission(56.3, 0.17)
    actual = heralded_success_probability(56.3, 0.17, 0.5, 0.5, 0.9)
    _, expected, _ = _decimal_oracle()

    assert actual == pytest.approx(0.5 * 0.5 * 0.9 * arm**2, abs=1e-15)
    assert actual == pytest.approx(float(expected), abs=1e-14)
    assert actual == pytest.approx(0.0248, abs=5e-5)


def test_v3_type_ii_rate_reproduces_paper_value():
    _, _, expected_rate = _decimal_oracle()

    result = type_ii_memory_rate(PAPER_PARAMETERS)

    assert result.per_memory_rate_hz == pytest.approx(float(expected_rate), abs=1e-10)
    assert result.per_memory_rate_hz == pytest.approx(106.0, abs=0.5)
    assert result.joint_two_arm_transmission == pytest.approx(
        result.per_arm_transmission**2,
        abs=1e-15,
    )


def test_decomposed_rate_matches_paper_general_closed_form():
    memory_count = 7
    parameters = TypeIIMemoryParameters(
        **{**PAPER_PARAMETERS.__dict__, "memory_count": memory_count}
    )
    expected = (
        memory_count
        * 2.0
        * 0.5
        * 0.5
        * 0.9
        * 10.0 ** (-0.1 * 0.17 * 56.3)
        / (56_300.0 * (1.0 / 2e8 + 1.0 / 3e8))
    )

    result = type_ii_memory_rate(parameters)

    assert result.effective_rate_hz == pytest.approx(expected, abs=1e-12)


def test_memory_multiplicity_is_linear_in_ding_m1_model():
    result = type_ii_memory_rate(
        TypeIIMemoryParameters(**{**PAPER_PARAMETERS.__dict__, "memory_count": 7})
    )

    assert result.effective_rate_hz == pytest.approx(
        7 * result.per_memory_rate_hz,
        abs=1e-12,
    )


def test_one_memory_meets_paper_100_hz_event_demand():
    per_memory_rate = type_ii_memory_rate(PAPER_PARAMETERS).per_memory_rate_hz

    assert minimum_memory_count_for_rate(100.0, per_memory_rate) == 1
    assert minimum_memory_count_for_rate(0.0, per_memory_rate) == 0


@pytest.mark.parametrize(
    ("field", "value", "exception"),
    [
        ("separation_km", 0.0, ValueError),
        ("fiber_speed_m_s", -1.0, ValueError),
        ("attenuation_db_per_km", -0.01, ValueError),
        ("projection_success_probability", 1.01, ValueError),
        ("collection_efficiency", float("nan"), ValueError),
        ("detector_efficiency", -0.1, ValueError),
        ("memory_count", 0, ValueError),
        ("memory_count", 1.5, TypeError),
    ],
)
def test_type_ii_parameters_reject_invalid_values(field, value, exception):
    values = {**PAPER_PARAMETERS.__dict__, field: value}

    with pytest.raises(exception):
        TypeIIMemoryParameters(**values)


def test_reproduction_experiment_passes_all_oracles(tmp_path):
    repository_root = Path(__file__).resolve().parents[2]
    config = (
        repository_root
        / "experiments"
        / "ding_jiang"
        / "configs"
        / "type_ii_memory_v3.json"
    )

    summary = reproduce(config, tmp_path)

    assert summary["overall_status"] == "PASS"
    assert all(
        validation["status"] == "PASS"
        for validation in summary["validations"].values()
    )
    assert (tmp_path / "type_ii_memory_summary.json").is_file()
    assert (tmp_path / "memory_rate_by_count.csv").is_file()
