# Li et al. v1 reproduction experiments

The experiments in this directory are configuration-driven reproductions of
arXiv:2604.07451v1. Generated data and validation summaries are committed so
that scientific regressions can be reviewed without rerunning plotting code.

## Figure 2

Run from the repository root:

```bash
PYTHONPATH=src python3 -m experiments.li2026.reproduce_fig2
```

Outputs are written to `experiments/li2026/results/fig2_v1/`:

- `fig2a_independent_gap.csv`: independent Bernoulli input surface;
- `fig2b_correlated_gap.csv`: correlated input surface;
- `fig2c_noisy_gap.csv`: symmetric and asymmetric noisy curves;
- `fig2c_threshold.csv`: fidelity-threshold inset data;
- `fig2_reproduction.png`: three-panel visualization;
- `fig2_summary.json`: configuration, extrema, and oracle results.

The paper does not provide author numerical data for Figure 2. The configured
analytical and independent-code validations can pass while the paper-item
reproduction status remains `PARTIAL`.

## Figure 3

Run from the repository root:

```bash
PYTHONPATH=src python3 -m experiments.li2026.reproduce_fig3
```

The experiment evaluates the exact binomial-tail requirement for the CHSH game
over combined infidelity, two significance levels, and three stationary-window
durations. Outputs are written to `experiments/li2026/results/fig3_v1/`.

## Table III 50 km benchmark

Run from the repository root:

```bash
PYTHONPATH=src python3 -m experiments.li2026.reproduce_table3_50km
```

The benchmark derives Eq. 54-61 quantities from separate device, network,
game, and application configuration blocks. Outputs are written to
`experiments/li2026/results/table3_50km_v1/`. The internal 60-digit Decimal
formula gate and the 10 ms/100 ms operational cases pass. Paper-level status is
`PARTIAL`: the output records four displayed-value inconsistencies while the
derived `R_HEG=7854.545 s^-1` reproduces the reported `7.9e3 s^-1`.

## M2 analytical/event-driven cross-validation

Run from the repository root:

```bash
PYTHONPATH=src python3 -m experiments.li2026.cross_validate_m2_event_simulation
```

The experiment runs 256 independent seeded replicates of the Table III memory
bank and writes replicate, convergence, event-trace, and summary artifacts to
`experiments/li2026/results/m2_event_cross_validation_v1/`. The committed run
contains 26,368,000 trials and obtains `7863.867 s^-1` with a 95% interval of
`[7826.764, 7900.970] s^-1`, containing the analytical `7854.545 s^-1`.
