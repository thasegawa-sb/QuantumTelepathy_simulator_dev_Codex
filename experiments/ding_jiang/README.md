# Ding-Jiang v3 Reproductions

Primary reference: Dawei Ding and Liang Jiang, "Coordinating Decisions via Quantum Telepathy", arXiv:2407.21723v3.

## Figure 3

The experiment evaluates the ideal hedging-game gap on a configuration-driven `p,beta` grid. It writes the full numerical grid, a validation summary, and a three-panel plot corresponding to paper Figure 3.

Run from the repository root:

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_fig3.py
```

The validation gate compares:

- the XOR classical value with an independent enumeration of all 16 deterministic local strategies;
- the `beta=0` cross-section with Theorem 10;
- the `beta -> 1-beta` symmetry;
- the zero gap at `beta=0.5`;
- the maximum gap with the analytical CHSH value.

The main paper does not state its surface-grid spacing. The default 0.01 spacing is a documented simulator choice. Appendix Figure 9 explicitly uses 0.1 spacing.
