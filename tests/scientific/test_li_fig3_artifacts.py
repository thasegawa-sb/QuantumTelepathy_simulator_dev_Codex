import csv
import json
from pathlib import Path

import pytest


RESULT_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "experiments" / "li2026" / "results" / "fig3_v1"
)


def _read_csv(name):
    with (RESULT_DIRECTORY / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_figure3_summary_records_validated_partial_reproduction():
    with (RESULT_DIRECTORY / "fig3_summary.json").open(encoding="utf-8") as stream:
        summary = json.load(stream)

    assert summary["reference"]["version"] == "v1"
    assert summary["overall_status"] == "PASS"
    assert summary["paper_reproduction_status"] == "PARTIAL"
    assert summary["grid"] == {
        "alpha_count": 2,
        "epsilon_count": 293,
        "point_count": 1758,
        "t_env_count": 3,
    }
    assert all(
        validation["status"] == "PASS"
        for validation in summary["validations"].values()
    )
    assert summary["simulator_extrema"]["maximum_required_trials_by_alpha"] == {
        "0.001": 17_946_458,
        "0.05": 5_083_117,
    }


def test_figure3_csv_artifacts_preserve_exact_round_counts_and_rate_scaling():
    points = _read_csv("fig3_required_rate.csv")
    reference = _read_csv("fig3_reference_points.csv")

    assert len(points) == 1758
    assert len(reference) == 6
    assert {
        (float(row["alpha"]), float(row["t_env_seconds"]), int(row["required_trials"]))
        for row in reference
    } == {
        (0.05, 0.001, 65),
        (0.05, 0.1, 65),
        (0.05, 10.0, 65),
        (0.001, 0.001, 238),
        (0.001, 0.1, 238),
        (0.001, 10.0, 238),
    }
    for row in reference:
        assert float(row["required_rate_hz"]) * float(
            row["t_env_seconds"]
        ) == pytest.approx(float(row["required_trials"]), abs=1e-12)
        assert float(row["certification_p_value"]) < float(row["alpha"])
        assert float(row["previous_round_p_value"]) >= float(row["alpha"])


def test_figure3_plot_artifact_is_nonempty():
    assert (RESULT_DIRECTORY / "fig3_reproduction.png").stat().st_size > 100_000
