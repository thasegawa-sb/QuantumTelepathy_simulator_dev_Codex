"""Run the Phase 15 final regression and reproduction audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).with_name("configs") / "phase15_v1.json"
DEFAULT_OUTPUT = Path(__file__).with_name("results") / "phase15_v1"
ALLOWED_MATRIX_STATUSES = {
    "PASS",
    "PARTIAL",
    "FAIL",
    "NOT_IMPLEMENTED",
    "INSUFFICIENT_INFORMATION",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant: {value}")
            ),
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _artifact_manifest(roots: list[str]) -> dict[str, Any]:
    files = sorted(
        path
        for root in roots
        for path in (ROOT / root).rglob("*")
        if path.is_file()
    )
    entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in files
    ]
    aggregate = hashlib.sha256(
        "".join(f"{item['path']}:{item['sha256']}\n" for item in entries).encode()
    ).hexdigest()
    return {
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "aggregate_sha256": aggregate,
        "files": entries,
    }


def _reference_has_version(value: Any, expected_version: str) -> bool:
    if isinstance(value, dict):
        if "version" in value:
            return value["version"] == expected_version
        return any(
            _reference_has_version(item, expected_version)
            for item in value.values()
        )
    if isinstance(value, list):
        return any(_reference_has_version(item, expected_version) for item in value)
    return False


def _compare_values(
    actual: Any,
    expected: Any,
    *,
    tolerance: float,
    ignored_fragments: tuple[str, ...],
    path: str = "$",
) -> tuple[int, float, list[str]]:
    if isinstance(actual, dict) and isinstance(expected, dict):
        actual_keys = {
            key
            for key in actual
            if not any(fragment in key.lower() for fragment in ignored_fragments)
        }
        expected_keys = {
            key
            for key in expected
            if not any(fragment in key.lower() for fragment in ignored_fragments)
        }
        mismatches = 0
        maximum_error = 0.0
        examples: list[str] = []
        if actual_keys != expected_keys:
            return 1, 0.0, [f"{path}: dictionary keys differ"]
        for key in sorted(actual_keys):
            count, error, child_examples = _compare_values(
                actual[key],
                expected[key],
                tolerance=tolerance,
                ignored_fragments=ignored_fragments,
                path=f"{path}.{key}",
            )
            mismatches += count
            maximum_error = max(maximum_error, error)
            examples.extend(child_examples[: 5 - len(examples)])
        return mismatches, maximum_error, examples
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return 1, 0.0, [f"{path}: list lengths differ"]
        mismatches = 0
        maximum_error = 0.0
        examples: list[str] = []
        for index, (actual_item, expected_item) in enumerate(
            zip(actual, expected, strict=True)
        ):
            count, error, child_examples = _compare_values(
                actual_item,
                expected_item,
                tolerance=tolerance,
                ignored_fragments=ignored_fragments,
                path=f"{path}[{index}]",
            )
            mismatches += count
            maximum_error = max(maximum_error, error)
            examples.extend(child_examples[: 5 - len(examples)])
        return mismatches, maximum_error, examples
    if isinstance(actual, bool) or isinstance(expected, bool):
        matches = actual is expected
        return (0, 0.0, []) if matches else (1, 0.0, [f"{path}: values differ"])
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        error = abs(float(actual) - float(expected))
        matches = math.isfinite(error) and error <= tolerance
        return (
            (0, error, [])
            if matches
            else (1, error, [f"{path}: numerical error {error:.3e}"])
        )
    matches = actual == expected
    return (0, 0.0, []) if matches else (1, 0.0, [f"{path}: values differ"])


def _run_job(
    job: dict[str, Any],
    temporary_root: Path,
    tolerance: float,
    ignored_fragments: tuple[str, ...],
) -> dict[str, Any]:
    output_directory = temporary_root / job["id"]
    output_directory.mkdir(parents=True)
    command = [
        sys.executable,
        str(ROOT / job["script"]),
        job["output_flag"],
        str(output_directory),
    ]
    command.extend(str(ROOT / item) if item.startswith("experiments/") else item for item in job.get("extra_args", []))
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(
            None,
            (str(ROOT / "src"), str(ROOT), environment.get("PYTHONPATH")),
        )
    )
    environment["MPLCONFIGDIR"] = str(temporary_root / "mpl" / job["id"])
    environment["XDG_CACHE_HOME"] = str(temporary_root / "cache" / job["id"])
    started = perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=1_800,
        check=False,
    )
    elapsed = perf_counter() - started
    generated_path = output_directory / job["summary_file"]
    committed_path = ROOT / job["committed_summary"]
    if not generated_path.exists():
        return {
            "id": job["id"],
            "status": "FAIL",
            "return_code": completed.returncode,
            "runtime_seconds": elapsed,
            "error": completed.stderr[-2000:],
        }
    generated = _load_json(generated_path)
    committed = _load_json(committed_path)
    mismatch_count, maximum_error, examples = _compare_values(
        generated,
        committed,
        tolerance=tolerance,
        ignored_fragments=ignored_fragments,
    )
    overall_status = generated.get("overall_status")
    version_matches = _reference_has_version(
        generated.get("reference", generated.get("references", {})),
        job["expected_version"],
    )
    status = (
        "PASS"
        if completed.returncode == 0
        and overall_status == "PASS"
        and mismatch_count == 0
        and version_matches
        else "FAIL"
    )
    return {
        "id": job["id"],
        "status": status,
        "return_code": completed.returncode,
        "runtime_seconds": elapsed,
        "overall_status": overall_status,
        "paper_reproduction_status": generated.get(
            "paper_reproduction_status",
            generated.get("reproduction_status"),
        ),
        "paper_version_matches": version_matches,
        "summary_comparison": {
            "mismatch_count": mismatch_count,
            "maximum_numeric_absolute_error": maximum_error,
            "tolerance": tolerance,
            "examples": examples,
        },
        "generated_summary_sha256": _sha256(generated_path),
        "committed_summary_sha256": _sha256(committed_path),
        "note": job.get("note"),
    }


def _matrix_audit() -> dict[str, Any]:
    matrix_path = ROOT / "docs/research/REPRODUCTION_MATRIX.md"
    statuses = []
    malformed_rows = []
    for line_number, line in enumerate(
        matrix_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] in {"Reference", "---"}:
            continue
        if len(cells) != 14:
            malformed_rows.append(line_number)
            continue
        statuses.append(cells[12])
    invalid_statuses = sorted(set(statuses) - ALLOWED_MATRIX_STATUSES)
    counts = Counter(statuses)
    return {
        "status": "PASS" if not malformed_rows and not invalid_statuses else "FAIL",
        "row_count": len(statuses),
        "status_counts": dict(sorted(counts.items())),
        "malformed_row_lines": malformed_rows,
        "invalid_statuses": invalid_statuses,
    }


def _configuration_audit() -> dict[str, Any]:
    paths = sorted(
        path
        for directory in ("configs", "oracles")
        for path in (ROOT / "experiments").rglob(f"{directory}/*.json")
    )
    failures = []
    for path in paths:
        try:
            _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            failures.append(f"{path.relative_to(ROOT)}: {error}")
    return {
        "status": "PASS" if not failures else "FAIL",
        "json_file_count": len(paths),
        "failures": failures,
    }


def _results_git_audit(result_roots: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no", "--", *result_roots],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed = [line for line in completed.stdout.splitlines() if line.strip()]
    return {
        "status": "PASS" if completed.returncode == 0 and not changed else "FAIL",
        "changed_paths": changed,
    }


def _run_tests() -> dict[str, Any]:
    started = perf_counter()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--ignore=tests/scientific/test_phase15_final_validation_artifacts.py",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = perf_counter() - started
    summary_line = next(
        (
            line.strip()
            for line in reversed(completed.stdout.splitlines())
            if " passed" in line or " failed" in line
        ),
        "",
    )
    return {
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "return_code": completed.returncode,
        "runtime_seconds": elapsed,
        "summary": summary_line,
        "stderr_tail": completed.stderr[-2000:],
    }


def validate(config_path: Path, output_directory: Path) -> dict[str, Any]:
    config = _load_json(config_path)
    tolerance = float(config["comparison_absolute_tolerance"])
    ignored = tuple(config["ignored_comparison_key_fragments"])
    manifest_before = _artifact_manifest(config["result_roots"])
    with tempfile.TemporaryDirectory(prefix="quantum_telepathy_phase15_") as temporary:
        temporary_root = Path(temporary)
        with ThreadPoolExecutor(max_workers=int(config["maximum_workers"])) as executor:
            jobs = list(
                executor.map(
                    lambda job: _run_job(
                        job,
                        temporary_root,
                        tolerance,
                        ignored,
                    ),
                    config["jobs"],
                )
            )
    manifest_after = _artifact_manifest(config["result_roots"])
    artifact_unchanged = (
        manifest_before["aggregate_sha256"] == manifest_after["aggregate_sha256"]
    )
    matrix = _matrix_audit()
    configurations = _configuration_audit()
    git_results = _results_git_audit(config["result_roots"])
    tests = _run_tests()
    validations = {
        "experiment_jobs": {
            "status": "PASS" if all(job["status"] == "PASS" for job in jobs) else "FAIL",
            "passed": sum(job["status"] == "PASS" for job in jobs),
            "total": len(jobs),
        },
        "committed_artifacts_unchanged": {
            "status": "PASS" if artifact_unchanged else "FAIL",
            "before_sha256": manifest_before["aggregate_sha256"],
            "after_sha256": manifest_after["aggregate_sha256"],
        },
        "result_worktree_clean": git_results,
        "configuration_json": configurations,
        "reproduction_matrix": matrix,
        "test_suite": tests,
    }
    overall_status = (
        "PASS"
        if all(validation["status"] == "PASS" for validation in validations.values())
        else "FAIL"
    )
    summary = {
        "schema_version": 1,
        "phase": config["phase"],
        "validation_id": config["validation_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "overall_status": overall_status,
        "jobs": jobs,
        "validations": validations,
        "committed_artifact_manifest": manifest_after,
        "notes": config["notes"],
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "final_validation_summary.json"
    with output_path.open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    summary = validate(arguments.config.resolve(), arguments.output.resolve())
    print(f"Overall status: {summary['overall_status']}")
    print(
        "Experiment jobs: "
        f"{summary['validations']['experiment_jobs']['passed']}/"
        f"{summary['validations']['experiment_jobs']['total']} PASS"
    )
    print(f"Tests: {summary['validations']['test_suite']['summary']}")
    raise SystemExit(0 if summary["overall_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
