import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = (
    ROOT
    / "experiments/performance/results/phase14_v1/phase14_benchmark_summary.json"
)


def _load_summary():
    with SUMMARY.open(encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant: {value}")
            ),
        )


def test_phase14_benchmark_and_all_validation_gates_pass():
    summary = _load_summary()

    assert summary["phase"] == 14
    assert summary["overall_status"] == "PASS"
    assert all(
        validation["status"] == "PASS"
        for validation in summary["validations"].values()
    )


def test_hardware_grid_is_faster_and_scientifically_identical():
    summary = _load_summary()
    hardware = summary["targets"]["hardware_grid"]
    validation = summary["validations"]["hardware_runtime"]
    signature = summary["validations"]["hardware_scientific_signature"]

    assert hardware["scientific_result"]["candidate_count"] == 43_776
    assert hardware["repeat_results_identical"] is True
    assert signature["actual"] == signature["expected"]
    assert validation["runtime_ratio"] <= validation["maximum_ratio"]
    assert hardware["peak_rss_bytes"] > 0


def test_statistics_minimality_and_figure5_sdp_bracket_are_preserved():
    summary = _load_summary()
    statistics_cases = summary["targets"]["finite_statistics"][
        "scientific_result"
    ]["cases"]
    sdp = summary["targets"]["figure5_sdp"]["scientific_result"]

    assert [case["n_req"] for case in statistics_cases] == [238, 66_133]
    assert all(
        case["p_value_at_n_req"] < case["alpha"]
        <= case["p_value_at_previous_round"]
        for case in statistics_cases
    )
    assert sdp["threshold_lower_bound"] <= 0.941
    assert 0.941 - sdp["threshold_lower_bound"] <= 0.02
    assert sdp["bracket_width"] <= 5e-4
    assert set(sdp["solver_statuses"]) <= {"optimal", "optimal_inaccurate"}
