import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY = (
    ROOT
    / "experiments/final_validation/results/phase15_v1/final_validation_summary.json"
)


def _load_summary():
    with SUMMARY.open(encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant: {value}")
            ),
        )


def test_phase15_summary_and_every_validation_gate_pass():
    summary = _load_summary()

    assert summary["phase"] == 15
    assert summary["overall_status"] == "PASS"
    assert all(
        validation["status"] == "PASS"
        for validation in summary["validations"].values()
    )


def test_all_reproduction_jobs_pass_and_retain_paper_versions():
    summary = _load_summary()

    assert len(summary["jobs"]) == 12
    assert all(job["status"] == "PASS" for job in summary["jobs"])
    assert all(job["overall_status"] == "PASS" for job in summary["jobs"])
    assert all(job["paper_version_matches"] is True for job in summary["jobs"])
    assert all(
        job["summary_comparison"]["mismatch_count"] == 0
        for job in summary["jobs"]
    )


def test_final_audits_preserve_artifacts_and_allowed_reproduction_statuses():
    summary = _load_summary()
    validations = summary["validations"]
    matrix = validations["reproduction_matrix"]

    assert (
        validations["committed_artifacts_unchanged"]["before_sha256"]
        == validations["committed_artifacts_unchanged"]["after_sha256"]
    )
    assert validations["result_worktree_clean"]["changed_paths"] == []
    assert validations["configuration_json"]["failures"] == []
    assert matrix["invalid_statuses"] == []
    assert matrix["malformed_row_lines"] == []
    assert matrix["status_counts"]["PARTIAL"] > 0
    assert matrix["status_counts"]["INSUFFICIENT_INFORMATION"] > 0
