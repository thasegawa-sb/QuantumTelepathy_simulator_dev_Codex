import csv
import json
import math
from pathlib import Path

import pytest

from quantum_telepathy.li2026.statistics import certification_p_value


ROOT = Path(__file__).resolve().parents[2]
RESULT_DIRECTORY = ROOT / "experiments/li2026/results/fig7b_v1"


def _summary():
    with (RESULT_DIRECTORY / "fig7b_summary.json").open(encoding="utf-8") as stream:
        return json.load(stream)


def test_fig7b_artifact_gate_passes_but_paper_status_remains_partial():
    summary = _summary()

    assert summary["reference"]["version"] == "v1"
    assert summary["overall_status"] == "PASS"
    assert summary["paper_reproduction_status"] == "PARTIAL"
    assert summary["grid"] == {
        "beta_count": 101,
        "point_count": 10201,
        "probability_count": 101,
    }
    assert all(item["status"] == "PASS" for item in summary["validations"].values())
    assert summary["operational_status_validation"]["status"] == "PASS"


def test_fig7b_maximum_and_limit_regions_match_analytical_oracles():
    summary = _summary()
    maximum = summary["simulator_extrema"]["maximum"]
    validations = summary["validations"]

    assert maximum["probability_one"] == 0.5
    assert maximum["beta"] == 0.0
    assert maximum["gap"] == pytest.approx(
        (math.sqrt(2.0) - 1.0) / 4.0, abs=1e-12
    )
    assert validations["beta_half_max_abs_gap"]["actual"] <= 1e-12
    assert validations["beta_upper_advantage_violation"]["actual"] <= 1e-12
    assert validations["input_boundary_max_abs_gap"]["actual"] <= 1e-12
    assert validations["p_reflection_symmetry_max_abs_error"]["actual"] <= 1e-12


def test_fig7b_independent_classical_and_quantum_cross_checks_are_tight():
    summary = _summary()
    validations = summary["validations"]

    assert validations["classical_enumeration_max_abs_error"]["actual"] <= 1e-12
    assert validations["quantum_cross_validation_max_abs_error"]["actual"] <= 2e-9
    assert len(summary["quantum_cross_validation"]) == 10


def test_representative_multiparty_certification_is_discretely_minimal():
    result = _summary()["representative_operational_case"]["result"]
    rounds = result["n_req"]

    assert result["statistics_method"] == "exact_binomial"
    assert result["overall_operational_quantum_advantage"] == "PASS"
    assert rounds == 107
    assert certification_p_value(
        rounds, result["classical_value"], result["noisy_quantum_value"]
    ) < result["alpha"]
    assert certification_p_value(
        rounds - 1, result["classical_value"], result["noisy_quantum_value"]
    ) >= result["alpha"]


def test_fig7b_grid_csv_and_plot_are_complete():
    with (RESULT_DIRECTORY / "fig7b_gap.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    plot = RESULT_DIRECTORY / "fig7b_reproduction.png"

    assert len(rows) == 10201
    assert {float(row["probability_one"]) for row in rows} == {
        index / 100 for index in range(101)
    }
    assert {float(row["beta"]) for row in rows} == {
        index / 100 for index in range(101)
    }
    assert plot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert plot.stat().st_size > 30_000
