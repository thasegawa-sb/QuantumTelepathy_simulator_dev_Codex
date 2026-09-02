import csv
import json
from pathlib import Path

import pytest


RESULT_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "li2026"
    / "results"
    / "table3_50km_v1"
)


def test_table3_summary_separates_formula_validation_from_paper_discrepancies():
    with (RESULT_DIRECTORY / "table3_summary.json").open(encoding="utf-8") as stream:
        summary = json.load(stream)

    assert summary["reference"]["version"] == "v1"
    assert summary["overall_status"] == "PASS"
    assert summary["paper_reproduction_status"] == "PARTIAL"
    assert summary["discrepancy_set_matches_oracle"]
    assert summary["observed_failed_paper_metrics"] == [
        "entanglement_success_probability",
        "false_positive_fraction",
        "intrinsic_heg_rate_hz",
        "tau_occ_seconds",
    ]
    assert all(
        validation["status"] == "PASS"
        for validation in summary["formula_validations"].values()
    )


def test_table3_derived_rate_error_and_operational_cases_are_reproducible():
    with (RESULT_DIRECTORY / "table3_summary.json").open(encoding="utf-8") as stream:
        summary = json.load(stream)

    result = summary["system_level_result"]
    assert result["rate"]["r_heg"] == pytest.approx(
        7854.545454545455, rel=1e-15
    )
    assert result["timing"]["tau_occ"] == pytest.approx(242.55e-6, abs=1e-18)
    assert result["combined_infidelity_upper_bound"] == pytest.approx(
        0.06089152, abs=1e-15
    )
    assert result["memory_adjusted_combined_infidelity_upper_bound"] < 0.061
    assert summary["memory_fidelity_result"]["memory_lifetime_criterion"]

    cases = summary["operational_cases"]
    assert [case["t_env"] for case in cases] == [0.01, 0.1]
    assert [case["n_req"] for case in cases] == [65, 65]
    assert [case["r_req"] for case in cases] == [6500.0, 650.0]
    assert all(
        case["overall_operational_quantum_advantage"] == "PASS" for case in cases
    )


def test_table3_comparison_csv_preserves_pass_and_fail_evidence():
    with (RESULT_DIRECTORY / "table3_paper_comparison.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 11
    assert sum(row["status"] == "PASS" for row in rows) == 7
    assert sum(row["status"] == "FAIL" for row in rows) == 4
    rate = next(row for row in rows if row["metric"] == "r_heg_hz")
    assert float(rate["actual"]) == pytest.approx(7854.545454545455, rel=1e-15)
    assert float(rate["absolute_error"]) <= float(rate["tolerance"])
