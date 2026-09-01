# Quantum Telepathy Simulator

Research scaffold for reproducing Ding-Jiang arXiv:2407.21723v3 and Li et al. arXiv:2604.07451v1.

Current state:

- Git repository initialized from an empty workspace.
- Research model maps and reproduction matrix live in `docs/research/`.
- Implemented gates cover CHSH, deterministic classical baselines, Ding-Jiang ideal HFT and representative direct-photon loss, Li generalized utility mapping, and Li's exact combined-infidelity expression.

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
