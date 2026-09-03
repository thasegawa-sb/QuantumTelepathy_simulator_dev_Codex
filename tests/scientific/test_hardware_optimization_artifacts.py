import csv
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "experiments/li2026/results/hardware_optimization_v1"
SUMMARY = RESULTS / "hardware_optimization_summary.json"
ORACLE = ROOT / "experiments/li2026/oracles/hardware_optimization_v1.json"


def _load(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant: {value}")
            ),
        )


def test_phase13_summary_and_every_validation_pass():
    summary = _load(SUMMARY)

    assert summary["overall_status"] == "PASS"
    assert summary["case_count"] == 9
    assert summary["search_space"]["candidate_count_per_case"] == 4864
    assert all(
        validation["status"] == "PASS"
        for validation in summary["validations"].values()
    )
    assert summary["optimization_claim"].startswith("Exact only on the configured")


def test_case_statuses_counts_and_recommendations_match_pinned_oracle():
    summary = _load(SUMMARY)
    oracle = _load(ORACLE)
    cases = {item["case_id"]: item for item in summary["cases"]}

    assert set(cases) == set(oracle["expected_search_status"])
    for case_id, expected in oracle["expected_search_status"].items():
        assert cases[case_id]["search_status"] == expected
        assert cases[case_id]["evaluated_count"] == 4864
        assert cases[case_id]["evaluation_error_count"] == 0
        assert (
            cases[case_id]["feasible_count"]
            == oracle["expected_feasible_counts"][case_id]
        )

    for case_id, expected in oracle["expected_recommended_designs"].items():
        design = cases[case_id]["recommended"]["design"]
        assert {key: design[key] for key in expected} == expected
        assert (
            cases[case_id]["recommended"]
            ["overall_operational_quantum_advantage"]
            == "PASS"
        )


def test_distance_envelope_and_50km_strict_channel_transition():
    summary = _load(SUMMARY)

    assert summary["distance_envelope"] == {
        "scenario_id": "ding_rate_stress_1s",
        "maximum_configured_feasible_distance_km": 125.0,
        "first_configured_infeasible_distance_km": 150.0,
    }
    transition = summary["analytical_channel_transitions"][
        "ding_rate_stress_1s@50km"
    ]
    assert transition["minimum_channels_analytical"] == 9
    assert transition["strict_transition_passes"] is True
    assert transition["per_channel_rate_hz"] == pytest.approx(
        7419.82758469439, rel=1e-15
    )


def test_correlated_case_exposes_joint_fidelity_and_rate_cost():
    summary = _load(SUMMARY)
    case = next(
        item
        for item in summary["cases"]
        if item["case_id"] == "correlated_asymmetric_fidelity_stress@50km"
    )
    baseline = case["baseline"]
    recommended = case["recommended"]

    assert "fidelity_criterion" in baseline["constraint_violations"]
    assert case["feasible_count"] == 2
    assert case["pareto_count"] == 1
    assert recommended["n_req"] == 1_132_017
    assert recommended["design"]["n_channels"] == 48
    assert recommended["r_heg"] > recommended["r_req"]
    assert recommended["weighted_cost"] == pytest.approx(7.0)


def test_committed_candidate_pareto_and_plot_artifacts_exist():
    summary = _load(SUMMARY)
    expected_rows = summary["case_count"] * summary["search_space"][
        "candidate_count_per_case"
    ]
    with (RESULTS / "hardware_candidates.csv").open(encoding="utf-8") as stream:
        assert sum(1 for _ in stream) == expected_rows + 1
    with (RESULTS / "pareto_front.csv").open(encoding="utf-8") as stream:
        pareto_rows = list(csv.DictReader(stream))
    with (RESULTS / "recommended_designs.csv").open(encoding="utf-8") as stream:
        recommended_rows = list(csv.DictReader(stream))

    assert len(pareto_rows) == sum(item["pareto_count"] for item in summary["cases"])
    assert len(recommended_rows) == 7
    image = RESULTS / "hardware_optimization.png"
    assert image.stat().st_size > 50_000
    assert image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
