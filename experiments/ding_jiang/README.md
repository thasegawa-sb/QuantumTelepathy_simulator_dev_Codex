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

## Section 4.1 Loss Example

The direct-photon experiment implements Equation A.11 as an explicit probability mixture and Equation A.12 as a lossy Bell operator. It enumerates all 16 local fallback strategies and applies the paper's 20-point angle grid before deterministic local refinement.

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_loss_example.py
```

The result reports the `p=0.3`, `beta=0.3`, `eta=0.95` lossy value, Schmidt coefficients, and a bracketed threshold efficiency.
