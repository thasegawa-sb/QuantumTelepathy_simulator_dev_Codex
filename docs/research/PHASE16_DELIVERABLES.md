# Phase 16 Documentation Deliverables

Completion date: 2026-09-03.

Source validation: `phase15_v1` (`PASS`).

## Final Narrative Artifacts

Phase 16 contains exactly the three requested narrative documents:

| Artifact | Format | Scope |
|---|---|---|
| `deliverables/phase16/quantum_telepathy_simulator_manual_ja.docx` | Japanese Word | Installation, execution, configuration, output interpretation, regression, extension, troubleshooting |
| `deliverables/phase16/quantum_telepathy_research_report_ja.docx` | Japanese Word | Research method, Ding-to-Li results, operational criteria, hardware, discrepancies, conclusions |
| `deliverables/phase16/operational_lctc_quantum_advantage.tex` | English LaTeX | Reproduction paper with equations, ten validated figures, a technology-context appendix, limitations, and bibliography |

`references.bib`, `figures/`, and the JSON manifest are supporting source/assets,
not additional narrative deliverables.

## Provenance

The Word builder reads the committed experiment JSON files directly. It does
not retype final scientific values or use expected paper values as model
inputs. The machine-readable artifact manifest is
`deliverables/phase16/phase16_document_manifest.json`.

The English paper includes copies of six committed reproduction figures and
four technology-context figures. The copies keep the LaTeX directory
self-contained; their source calculations, CSV data, and literature-provenance
JSON remain under `experiments/`.

## Word QA

Both documents were generated with `python-docx`, converted with LibreOffice
26.8.0, and rasterized with Poppler for page-by-page visual inspection. The
Japanese QA render explicitly used Homebrew Fontconfig and Noto Sans CJK JP so
the temporary LibreOffice profile could resolve Japanese glyphs.

| Check | Manual | Report |
|---|---:|---:|
| Rendered pages | 12 | 14 |
| Visual page inspection | PASS | PASS |
| Clipped/overlapping content | 0 | 0 |
| Accessibility audit findings | 0 | 0 |
| Heading audit | 15 H1 / 12 H2 | 13 H1 / 8 H2 |
| Embedded figures with alt text | 2 | 6 |

The visual pass checked the cover, every table continuation, all figures,
headers/footers, page-number fields, the last page, and the removal of sparse
TOC-only pages.

## LaTeX QA

Tectonic 0.17.0 compiled the paper with BibTeX and all ten local figures. The
final QA PDF was written only to a temporary directory and is not a fourth
narrative deliverable.

| Check | Result |
|---|---:|
| Compiled pages | 18 |
| Blocking TeX warnings | 0 |
| Non-blocking underfull bibliography boxes | 1 |
| Undefined citations/references | 0 |
| Missing figure assets | 0 |
| Full-page visual inspection | PASS |

## Reproduction

```bash
python3 tools/build_phase16_documents.py
python3 experiments/li2026/technology_benchmark/plot_technology_benchmarks.py
python3 -m pytest tests/scientific/test_phase16_deliverables.py -q
python3 -m pytest tests/scientific/test_li2026_technology_benchmark.py -q

cd deliverables/phase16
tectonic --outdir /tmp/quantum_telepathy_latex operational_lctc_quantum_advantage.tex
```

For a Japanese LibreOffice QA render on macOS, Noto Sans CJK JP must be visible
to Fontconfig. Microsoft Word can use its own compatible Japanese font
substitution when the named font is unavailable.

## Scientific Boundary

The documentation preserves the reproduction matrix status language. It does
not promote plot-level `PARTIAL`, microscopic-model
`INSUFFICIENT_INFORMATION`, or generic optimizer `NOT_IMPLEMENTED` items to
`PASS`. The documents also state that the HFT scenarios are sensitivity
analyses rather than empirical trading-profit claims.
