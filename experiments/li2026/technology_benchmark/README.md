# Li 2026 technology benchmark context

This experiment places the independent and derived parameters of the Li et al.
Table III 50-km design beside time-stamped primary research results and official
manufacturer specifications current to 2026-09-03.

Run from the repository root:

```bash
python3 experiments/li2026/technology_benchmark/plot_technology_benchmarks.py
```

The command writes four figures, a flattened point table, and a checksum summary
under `results/technology_benchmark_v1/`, then copies the figures used by the
English paper to `deliverables/phase16/figures/`.

## Interpretation rules

- `benchmark` identifies Li et al. inputs or model outputs, not measured values.
- `measured` identifies a research experiment.
- `record` is used only when the primary source explicitly claims a record or
  state-of-the-art result.
- `projected` identifies a published model or proposed architecture.
- `commercial` identifies an official orderable-subsystem specification; it
  does not mean that a turnkey quantum-network node can be purchased.
- Cross-platform or differently defined values are retained only as explicitly
  labelled proxies. Scatter points are not connected because they do not form a
  homogeneous longitudinal dataset.

The JSON file is the source of truth for plotted values, qualifiers, evidence
classes, source identifiers, URLs, and comparability notes. The Appendix source
table in the paper maps every bracketed plot label to a bibliography entry.
