import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest


RESULT_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "experiments"
    / "li2026"
    / "results"
    / "m2_event_cross_validation_v1"
)


def _read_csv(name):
    with (RESULT_DIRECTORY / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_event_cross_validation_summary_records_statistical_evidence():
    with (RESULT_DIRECTORY / "m2_event_summary.json").open(
        encoding="utf-8"
    ) as stream:
        summary = json.load(stream)

    assert summary["reference"]["version"] == "v1"
    assert summary["overall_status"] == "PASS"
    assert all(
        validation["status"] == "PASS"
        for validation in summary["validations"].values()
    )
    monte_carlo = summary["monte_carlo"]
    analytical = summary["analytical_oracle"]
    rate_statistics = monte_carlo["bell_pair_rate_statistics"]
    assert monte_carlo["replicates"] == 256
    assert monte_carlo["total_heralded_trials"] == 26_368_000
    assert monte_carlo["total_successful_heralds"] == 201_315
    assert rate_statistics["mean"] == pytest.approx(7863.8671875, abs=1e-12)
    assert (
        rate_statistics["confidence_interval_lower"]
        <= analytical["bell_pair_rate_hz"]
        <= rate_statistics["confidence_interval_upper"]
    )
    assert abs(monte_carlo["standardized_binomial_residual"]) < 1.0
    assert monte_carlo["total_wall_clock_seconds"] > 0.0
    assert summary["occupancy_time_distribution"] == [
        {"duration": 0.1, "fraction": 1.0, "occupied_memories": 250}
    ]


def test_replicate_and_convergence_artifacts_preserve_sample_accounting():
    replicates = _read_csv("m2_event_replicates.csv")
    convergence = _read_csv("m2_event_convergence.csv")

    assert len(replicates) == 256
    assert len({int(row["seed"]) for row in replicates}) == 256
    assert {int(row["heralded_trials"]) for row in replicates} == {103_000}
    assert sum(int(row["successful_heralds"]) for row in replicates) == 201_315
    assert max(int(row["peak_occupied_memories"]) for row in replicates) == 250
    assert all(
        float(row["mean_occupied_memories"])
        == pytest.approx(250.0, abs=1e-9)
        for row in replicates
    )

    assert [int(row["replicates"]) for row in convergence] == [
        16,
        32,
        64,
        128,
        256,
    ]
    standard_errors = [float(row["standard_error_hz"]) for row in convergence]
    assert all(
        right < left for left, right in zip(standard_errors, standard_errors[1:])
    )


def test_trace_records_attempt_herald_and_release_delays():
    trace = _read_csv("m2_event_trace.csv")
    event_counts = Counter(row["event_type"] for row in trace)
    by_attempt = defaultdict(list)
    for row in trace:
        by_attempt[int(row["attempt_id"])].append(row)

    assert len(trace) == 24
    assert event_counts["ATTEMPT_START"] == 8
    assert event_counts["HERALD_SUCCESS"] + event_counts["HERALD_FAILURE"] == 8
    assert event_counts["MEMORY_RELEASE"] == 8
    assert set(by_attempt) == set(range(8))
    for events in by_attempt.values():
        ordered = sorted(events, key=lambda row: float(row["time_seconds"]))
        start = next(row for row in ordered if row["event_type"] == "ATTEMPT_START")
        herald = next(
            row for row in ordered if row["event_type"].startswith("HERALD_")
        )
        release = next(
            row for row in ordered if row["event_type"] == "MEMORY_RELEASE"
        )
        start_time = float(start["time_seconds"])
        assert float(herald["time_seconds"]) - start_time == pytest.approx(
            240.58e-6, abs=1e-18
        )
        assert float(release["time_seconds"]) - start_time == pytest.approx(
            242.55e-6, abs=1e-18
        )
