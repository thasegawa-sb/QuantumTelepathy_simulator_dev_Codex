import csv
import hashlib
import json
from pathlib import Path

import pytest

from quantum_telepathy.li2026.statistics import score_certification_p_value


ROOT = Path(__file__).resolve().parents[2]
RESULT_DIRECTORY = ROOT / "experiments/li2026/results/hft_waterfall_v1"
SUMMARY_PATH = RESULT_DIRECTORY / "hft_waterfall_summary.json"


def _summary():
    with SUMMARY_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def test_hft_waterfall_artifact_gate_passes_with_expected_case_counts():
    summary = _summary()

    assert summary["references"]["ding_jiang"]["version"] == "v3"
    assert summary["references"]["li2026"]["version"] == "v1"
    assert summary["overall_status"] == "PASS"
    assert summary["scenario_count"] == 8
    assert summary["overall_pass_count"] == 3
    assert summary["overall_fail_count"] == 5
    assert all(item["status"] == "PASS" for item in summary["validations"].values())
    assert all(
        item["status"] == "PASS"
        for item in summary["scenario_validations"].values()
    )


def test_hardware_provenance_hash_matches_committed_table3_source():
    summary = _summary()
    source = ROOT / summary["hardware_provenance"]["source_file"]

    assert hashlib.sha256(source.read_bytes()).hexdigest() == summary[
        "hardware_provenance"
    ]["source_sha256"]
    assert summary["hardware_provenance"]["epsilon"] == pytest.approx(
        0.060972738493541345, abs=1e-15
    )
    assert summary["hardware_provenance"]["r_heg_hz"] == pytest.approx(
        7854.545454545455, rel=1e-15
    )


def test_general_score_scenarios_preserve_discrete_minimality():
    summary = _summary()
    indexed = {result["scenario_id"]: result for result in summary["results"]}

    for scenario_id in (
        "ding_representative_10s",
        "correlated_asymmetric_generalized",
    ):
        result = indexed[scenario_id]
        rounds = result["n_req"]
        assert result["statistics_method"] == "general_score_bound"
        assert score_certification_p_value(
            rounds,
            result["li_classical_value"],
            result["noisy_quantum_value"],
            result["score_min"],
            result["score_max"],
        ) < result["alpha"]
        assert score_certification_p_value(
            rounds - 1,
            result["li_classical_value"],
            result["noisy_quantum_value"],
            result["score_min"],
            result["score_max"],
        ) >= result["alpha"]


def test_stage_csv_contains_complete_ordered_waterfalls():
    with (RESULT_DIRECTORY / "hft_waterfall_stages.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 56
    by_scenario = {}
    for row in rows:
        by_scenario.setdefault(row["scenario_id"], []).append(int(row["order"]))
    assert len(by_scenario) == 8
    assert all(sorted(orders) == list(range(1, 8)) for orders in by_scenario.values())


def test_waterfall_plot_is_a_nonempty_png():
    plot = RESULT_DIRECTORY / "hft_waterfall.png"

    assert plot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert plot.stat().st_size > 50_000
