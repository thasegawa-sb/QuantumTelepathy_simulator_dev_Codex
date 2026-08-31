# Quantum Telepathy Simulator

Research scaffold for reproducing Ding-Jiang arXiv:2407.21723v3 and Li et al. arXiv:2604.07451v1.

Current state:

- Git repository initialized from an empty workspace.
- Research model maps and reproduction matrix live in `docs/research/`.
- The first implemented validation gate covers CHSH, deterministic classical baselines, Ding-Jiang HFT utility mapping, Li generalized utility mapping, and Li's exact combined-infidelity expression.

Run tests:

```bash
python3 -m pytest
```
