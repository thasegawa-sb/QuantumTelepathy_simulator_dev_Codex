import csv
import json
import math
from pathlib import Path

import pytest


RESULT_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "experiments" / "li2026" / "results" / "fig2_v1"
)


def _read_csv(name):
    with (RESULT_DIRECTORY / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_figure2_summary_records_validated_partial_reproduction():
    with (RESULT_DIRECTORY / "fig2_summary.json").open(encoding="utf-8") as stream:
        summary = json.load(stream)

    assert summary["reference"]["version"] == "v1"
    assert summary["overall_status"] == "PASS"
    assert summary["paper_reproduction_status"] == "PARTIAL"
    assert all(
        validation["status"] == "PASS"
        for validation in summary["validations"].values()
    )
    assert summary["grid"]["panel_a"]["point_count"] == 10201
    assert summary["grid"]["panel_b"]["point_count"] == 10201
    assert summary["grid"]["panel_c"]["curve_point_count"] == 3208
    assert summary["simulator_extrema"]["panel_a_maximum_gap"]["gap"] == pytest.approx(
        (math.sqrt(2.0) - 1.0) / 4.0, abs=1e-12
    )


def test_figure2_csv_artifacts_have_configured_rows_and_independent_oracles():
    panel_a = _read_csv("fig2a_independent_gap.csv")
    panel_b = _read_csv("fig2b_correlated_gap.csv")
    noisy = _read_csv("fig2c_noisy_gap.csv")
    thresholds = _read_csv("fig2c_threshold.csv")

    assert len(panel_a) == 10201
    assert len(panel_b) == 10201
    assert len(noisy) == 3208
    assert len(thresholds) == 202
    assert max(float(row["classical_oracle_abs_error"]) for row in panel_a + panel_b) <= 1e-12
    assert {int(row["deterministic_strategy_count"]) for row in panel_a + panel_b} == {16}

    chsh_threshold = next(
        row
        for row in thresholds
        if row["utility_family"] == "symmetric" and float(row["beta1"]) == 0.0
    )
    assert float(chsh_threshold["epsilon_threshold"]) == pytest.approx(
        1.0 - 1.0 / math.sqrt(2.0), abs=1e-12
    )


def test_figure2_plot_artifact_is_nonempty():
    assert (RESULT_DIRECTORY / "fig2_reproduction.png").stat().st_size > 100_000
