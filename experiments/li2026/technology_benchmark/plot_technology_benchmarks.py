"""Generate the literature-context figures used in the Phase 16 appendix."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA = Path(__file__).with_name("technology_benchmark_v1.json")
DEFAULT_RESULT_DIR = Path(__file__).with_name("results") / "technology_benchmark_v1"
DEFAULT_PAPER_FIGURE_DIR = ROOT / "deliverables" / "phase16" / "figures"

STYLES = {
    "benchmark": {"color": "#C43C35", "marker": "*", "size": 115},
    "measured": {"color": "#167D8D", "marker": "o", "size": 54},
    "record": {"color": "#6C4E9B", "marker": "D", "size": 55},
    "projected": {"color": "#D17A22", "marker": "^", "size": 62},
    "commercial": {"color": "#3A7D44", "marker": "s", "size": 58},
}

LEGEND_LABELS = {
    "benchmark": "Li benchmark/model",
    "measured": "Measured research",
    "record": "Measured, source claims record",
    "projected": "Published projection",
    "commercial": "Official commercial specification",
}

ANNOTATION_OFFSETS = (
    (5, 6),
    (5, -13),
    (-20, 6),
    (-20, -13),
    (8, 15),
    (-22, 15),
)


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _point_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sources = data["sources"]
    for figure in data["figures"]:
        for series in figure["series"]:
            for point in series["points"]:
                source = sources[point["source"]]
                rows.append(
                    {
                        "figure": figure["filename"],
                        "parameter": series["key"],
                        "source_id": point["source"],
                        "year": source["year"],
                        "value": point["value"],
                        "error": point.get("error", ""),
                        "qualifier": point.get("qualifier", "="),
                        "evidence": source["evidence"],
                        "source": source["short"],
                        "bibkey": source["bibkey"],
                        "note": point["note"],
                        "url": source["url"],
                    }
                )
    return rows


def _draw_series(ax: plt.Axes, series: dict[str, Any], sources: dict[str, Any]) -> None:
    collision_count: Counter[tuple[int, str]] = Counter()
    for point in series["points"]:
        source_id = point["source"]
        source = sources[source_id]
        year = int(source["year"])
        value = float(point["value"])
        evidence = source["evidence"]
        style = STYLES[evidence]

        if "error" in point:
            ax.errorbar(
                year,
                value,
                yerr=float(point["error"]),
                fmt=style["marker"],
                color=style["color"],
                markeredgecolor="white",
                markeredgewidth=0.7,
                markersize=(style["size"] ** 0.5),
                capsize=2.5,
                linewidth=1,
                zorder=3,
            )
        else:
            ax.scatter(
                year,
                value,
                color=style["color"],
                marker=style["marker"],
                edgecolor="white",
                linewidth=0.7,
                s=style["size"],
                zorder=3,
            )

        collision_key = (year, source_id)
        offset = ANNOTATION_OFFSETS[collision_count[collision_key] % len(ANNOTATION_OFFSETS)]
        collision_count[collision_key] += 1
        ax.annotate(
            f"[{source_id}]",
            (year, value),
            xytext=offset,
            textcoords="offset points",
            fontsize=7.4,
            color="#20252A",
            fontweight="bold" if evidence == "benchmark" else "normal",
            zorder=4,
        )

    years = sorted({int(sources[p["source"]]["year"]) for p in series["points"]})
    ax.set_xlim(min(years) - 0.8, max(years) + 0.8)
    if len(years) <= 8:
        ax.set_xticks(years)
    ax.set_xlabel("Year")
    ax.set_ylabel(series["ylabel"])
    ax.set_title(series["title"], fontsize=10.2, fontweight="semibold", pad=7)
    ax.set_yscale(series.get("yscale", "linear"))
    if "ylim" in series:
        ax.set_ylim(*series["ylim"])
    ax.grid(axis="y", color="#D8DADD", linewidth=0.7, alpha=0.8)
    ax.grid(axis="x", color="#ECEDEF", linewidth=0.5, alpha=0.55)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)


def _legend_handles(data: dict[str, Any]) -> list[Line2D]:
    present = {
        data["sources"][point["source"]]["evidence"]
        for figure in data["figures"]
        for series in figure["series"]
        for point in series["points"]
    }
    return [
        Line2D(
            [0],
            [0],
            marker=STYLES[key]["marker"],
            color="none",
            markerfacecolor=STYLES[key]["color"],
            markeredgecolor="white",
            markersize=7.5,
            label=LEGEND_LABELS[key],
        )
        for key in STYLES
        if key in present
    ]


def generate_figures(data: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.labelcolor": "#30353A",
            "xtick.color": "#4B5055",
            "ytick.color": "#4B5055",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    generated: list[Path] = []
    handles = _legend_handles(data)

    for figure_spec in data["figures"]:
        rows, columns = figure_spec["layout"]
        width = 5.1 * columns
        height = 3.45 * rows + 0.85
        figure, axes = plt.subplots(rows, columns, figsize=(width, height), squeeze=False)
        flat_axes = list(axes.flat)
        for ax, series in zip(flat_axes, figure_spec["series"], strict=False):
            _draw_series(ax, series, data["sources"])
        for ax in flat_axes[len(figure_spec["series"]):]:
            ax.axis("off")

        figure.suptitle(figure_spec["title"], fontsize=15, fontweight="bold", y=0.985)
        figure.legend(
            handles=handles,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.955),
            ncol=min(5, len(handles)),
            frameon=False,
            fontsize=8.2,
        )
        figure.text(
            0.5,
            0.012,
            f"Bracketed labels map to the appendix source table. Evidence current to {data['as_of_date']}.",
            ha="center",
            fontsize=7.8,
            color="#555A60",
        )
        figure.tight_layout(rect=(0.025, 0.045, 0.985, 0.92), h_pad=2.1, w_pad=1.5)
        output_path = output_dir / figure_spec["filename"]
        figure.savefig(output_path, dpi=240, bbox_inches="tight", facecolor="white")
        plt.close(figure)
        generated.append(output_path)
    return generated


def _write_rows(rows: list[dict[str, Any]], output_path: Path) -> None:
    fieldnames = list(rows[0])
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--paper-figure-dir", type=Path, default=DEFAULT_PAPER_FIGURE_DIR)
    parser.add_argument("--no-paper-copy", action="store_true")
    args = parser.parse_args()

    data = _load(args.data)
    rows = _point_rows(data)
    generated = generate_figures(data, args.result_dir)
    _write_rows(rows, args.result_dir / "technology_benchmark_points.csv")

    if not args.no_paper_copy:
        args.paper_figure_dir.mkdir(parents=True, exist_ok=True)
        for path in generated:
            shutil.copyfile(path, args.paper_figure_dir / path.name)

    summary = {
        "schema_version": data["schema_version"],
        "as_of_date": data["as_of_date"],
        "source_count": len(data["sources"]),
        "parameter_count": sum(len(item["series"]) for item in data["figures"]),
        "point_count": len(rows),
        "evidence_counts": dict(sorted(Counter(row["evidence"] for row in rows).items())),
        "figures": {path.name: _sha256(path) for path in generated},
    }
    with (args.result_dir / "technology_benchmark_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
