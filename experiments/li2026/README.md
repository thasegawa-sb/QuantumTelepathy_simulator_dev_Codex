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
