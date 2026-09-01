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

## Figure 5 Loss-Threshold Cross-Sections

The Figure 5 experiment evaluates the `p=0.5` beta cross-section and the `beta=0.4` input-probability cross-section on a documented 0.1 grid. For each point it reports two distinct numerical quantities: an upper bound on `eta*` from an explicit qubit strategy and a lower bound from a real-moment NPA `Q1+AB` relaxation.

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_fig5_cross_sections.py
```

The explicit search evaluates the Appendix B.3 20-point angle grid for all 16 deterministic fallbacks, then applies deterministic Powell refinement to the best two grid starts per fallback. It does not locally refine all 400 starts. The standard `Q1+AB` implementation is independent of that search but is not the paper's unpublished modified-NPA code and is not a machine-certified SDP proof. The committed result is therefore `PARTIAL` despite passing the CHSH endpoints, symmetry gates, bracket ordering, and the published `p=0.3`, `beta=0.3`, `eta* approximately 0.941` value. A full fresh run takes about 9.6 minutes on the recorded machine.

## Section 4.2 Type II Quantum Memory

The Type II experiment evaluates the v3 traversal-dominated M1 estimate, including the fiber photon flight, free-space herald return, two-arm transmission, heralded success probability, and ideal linear memory multiplicity.

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_type_ii_memory.py
```

The exact formula-derived values are checked against an independent Decimal oracle. The separately reported paper values are rounded, so their validation tolerances reflect the stated precision. This model does not include memory occupancy, reset timing, finite lifetime, or decoherence; those belong to the later Li M2 model.

## Figures 7-8 Depolarizing Noise

This experiment implements the rank-one qubit behavior in Equation 4.2, independently verifies the uniform-output utility in Equation 4.3, and evaluates robustness and noisy advantage over the configured `p,beta` grid.

```bash
PYTHONPATH=src python3 experiments/ding_jiang/reproduce_noise_robustness.py
```

The signed noisy gap is retained in CSV output; only the plotted surface is clipped to zero where no quantum advantage remains. The experiment does not reinterpret the paper's qubit depolarizing strength `nu` as Li's combined infidelity `epsilon`, and it does not model the higher-dimensional rank-dependent behavior discussed in Appendix A.4.
