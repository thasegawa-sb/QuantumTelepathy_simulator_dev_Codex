# Quantum Telepathy Simulator

Research scaffold for reproducing Ding-Jiang arXiv:2407.21723v3 and Li et al. arXiv:2604.07451v1.

Current state:

- Git repository initialized from an empty workspace.
- Research model maps and reproduction matrix live in `docs/research/`.
- Implemented gates cover CHSH, deterministic classical baselines, Ding-Jiang ideal HFT, direct-photon loss with Figure 5 cross-sections and an independent NPA bound, v3 Type II memory rate, and qubit depolarizing-noise robustness. Li support now includes generalized/asymmetric utility, correlated inputs, exact state and measurement infidelity, Figures 2-3, exact win/loss and bounded-score statistics, all operational criteria, M2 hardware, the 50 km benchmark, event-driven cross-validation, the HFT operational waterfall, and the three-party XOR/GHZ Figure 7(b) model.

Run tests:

```bash
python3 -m pytest
```

Reproduce Ding-Jiang v3 Figure 3:

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_fig3.py
```

Reproduce the Ding-Jiang v3 Section 4.1 loss example:

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_loss_example.py
```

Reproduce the Ding-Jiang v3 Figure 5(b,c) loss-threshold cross-sections:

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_fig5_cross_sections.py
```

Reproduce the Ding-Jiang v3 Section 4.2 Type II memory calculation:

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_type_ii_memory.py
```

Reproduce Ding-Jiang v3 Figures 7-8:

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_noise_robustness.py
```

Reproduce Li et al. v1 Figure 2:

```bash
PYTHONPATH=src python3 -m experiments.li2026.reproduce_fig2
```

Reproduce Li et al. v1 Figure 3:

```bash
PYTHONPATH=src python3 -m experiments.li2026.reproduce_fig3
```

Generate the Ding-to-Li HFT operational waterfall:

```bash
PYTHONPATH=src python3 -m experiments.li2026.analyze_hft_waterfall
```

Reproduce Li et al. v1 Figure 7(b):

```bash
PYTHONPATH=src python3 -m experiments.li2026.reproduce_fig7b
```
