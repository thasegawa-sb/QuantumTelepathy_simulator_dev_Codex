import csv
import json
from pathlib import Path

import pytest


RESULT_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "ding_jiang"
    / "results"
    / "fig5_cross_sections_v3"
)


def _summary():
    with (RESULT_DIRECTORY / "fig5_cross_sections_summary.json").open(
        encoding="utf-8"
    ) as stream:
        return json.load(stream)


def test_committed_fig5_cross_section_summary_passes_configured_gates():
    summary = _summary()
    representative = summary["results"]["representative_point"]

    assert summary["overall_status"] == "PASS"
    assert summary["reproduction_status"] == "PARTIAL"
    assert summary["results"]["unique_points"] == 22
    assert summary["results"]["npa_inaccurate_solver_calls"] == 0
    assert representative["strategy_transition"] == pytest.approx(0.941, abs=0.002)
    assert representative["npa_threshold_lower_bound"] <= 0.94140625
    assert all(
        validation["status"] == "PASS"
        for validation in summary["validations"].values()
    )


def test_committed_fig5_cross_section_artifacts_are_complete():
    with (RESULT_DIRECTORY / "fig5_cross_sections.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 22
    assert {row["cross_section"] for row in rows} == {
        "fig5b_beta_at_p_0_5",
        "fig5c_p_at_beta_0_4",
    }
    assert all(float(row["numerical_bracket_order_violation"]) == 0.0 for row in rows)
    assert (RESULT_DIRECTORY / "fig5_cross_sections.png").stat().st_size > 10_000
