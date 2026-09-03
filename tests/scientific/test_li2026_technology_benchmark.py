"""Scientific provenance checks for the Li 2026 technology-context audit."""

from __future__ import annotations

import csv
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments" / "li2026" / "technology_benchmark"
DATA = EXPERIMENT / "technology_benchmark_v1.json"
RESULTS = EXPERIMENT / "results" / "technology_benchmark_v1"
PAPER_FIGURES = ROOT / "deliverables" / "phase16" / "figures"


def _png_dimensions(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", raw[16:24])


def test_technology_dataset_has_complete_provenance() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert data["as_of_date"] == "2026-09-03"
    assert set(data["evidence_classes"]) == {
        "benchmark",
        "measured",
        "record",
        "projected",
        "commercial",
    }
    assert set(data["sources"]) == {str(value) for value in range(1, 26)}
    assert data["sources"]["1"]["bibkey"] == "li2026"

    points = [
        point
        for figure in data["figures"]
        for series in figure["series"]
        for point in series["points"]
    ]
    parameter_keys = {
        series["key"]
        for figure in data["figures"]
        for series in figure["series"]
    }
    assert len(data["figures"]) == 4
    assert len(parameter_keys) == 15
    assert len(points) == 68
    assert {point["source"] for point in points} == set(data["sources"])
    assert all(float(point["value"]) > 0.0 for point in points)
    assert all(point["note"].strip() for point in points)


def test_li_points_match_the_50km_configuration() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    config = json.loads(
        (ROOT / "experiments/li2026/configs/table3_50km_v1.json").read_text(
            encoding="utf-8"
        )
    )
    li_points = {
        series["key"]: [
            point["value"] for point in series["points"] if point["source"] == "1"
        ]
        for figure in data["figures"]
        for series in figure["series"]
    }
    assert li_points["internal_cooperativity"] == [
        config["device"]["internal_cooperativity"]
    ]
    assert li_points["memory_qubits"] == [config["device"]["n_memory_qubits"]]
    assert li_points["memory_coherence"] == [
        config["device"]["memory_lifetime_seconds"]
    ]
    assert li_points["detector_efficiency"] == [
        config["device"]["detector_efficiency"]
    ]
    assert li_points["dark_count_rate"] == [config["network"]["dark_count_rate_hz"]]
    assert li_points["fiber_attenuation"] == [
        config["network"]["attenuation_db_per_km"]
    ]
    assert li_points["remote_fiber_length"] == [config["network"]["distance_km"]]


def test_generated_outputs_are_complete_and_paper_ready() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    summary = json.loads(
        (RESULTS / "technology_benchmark_summary.json").read_text(encoding="utf-8")
    )
    with (RESULTS / "technology_benchmark_points.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert summary["source_count"] == 25
    assert summary["parameter_count"] == 15
    assert summary["point_count"] == len(rows) == 68
    assert sum(summary["evidence_counts"].values()) == 68
    for figure in data["figures"]:
        result_path = RESULTS / figure["filename"]
        paper_path = PAPER_FIGURES / figure["filename"]
        assert result_path.read_bytes() == paper_path.read_bytes()
        width, height = _png_dimensions(result_path)
        assert width >= 2000
        assert height >= 1000
