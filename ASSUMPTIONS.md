# Assumptions

| ID | Assumption | Status |
|---|---|---|
| A1 | This repository was intentionally initialized from an empty workspace on 2026-09-01. | Confirmed by user |
| A2 | Ding-Jiang reproduction is pinned to arXiv:2407.21723v3 unless explicitly changed. | Active |
| A3 | Li et al. reproduction is pinned to arXiv:2604.07451v1 unless a newer version is explicitly selected. | Active |
| A4 | The 2x2 XOR quantum bias can be computed by reducing Tsirelson's vector optimization to a one-dimensional maximization over the inner product of Bob's two vectors. | Tested against CHSH and Ding Theorem 10 samples |
| A5 | Li Eq. 25 is implemented with right-bottom matrix entry `-P(1,1)` because Eq. 35 requires the CHSH limit `1/4 [[1,1],[1,-1]]`. | Active |
| A6 | Ding-Jiang's depolarizing `nu` and Li's combined infidelity `epsilon` are distinct model parameters. | Active |
| A7 | Pointwise tolerances for plot-only paper results remain unset unless equations, author data, or documented digitization uncertainty provides an oracle. | Active |
| A8 | Ding-Jiang Figure 3 main-panel grid spacing is not specified; the reproduction uses 0.01 over `[0,1]^2`. | Active; Appendix Figure 9 separately specifies 0.1. |
| A9 | For the Ding HFT action labels, output 0 is `ask_first` and output 1 is `bid_first`. | Matches the paper's A/B utility columns and reported fallback strategy. |
| A10 | The representative loss threshold is bracketed using an advantage tolerance of `1e-9` and efficiency width `2e-5`. | Numerical criterion is explicit and configuration-driven. |
| A11 | Ding-Jiang Type II is a traversal-dominated M1 system estimate with independent identical memories and ideal linear scaling `r_e=M p_s/t_a`; it omits memory-photon operation time, occupancy, reset, finite lifetime, and decoherence. | Active only for Ding v3 reproduction; must not be substituted for Li M2. |
| A12 | Ding-Jiang's `t_a approx 230 us` is a two-significant-figure publication value; the listed inputs evaluate to `234.583 us`. | Exact formula is the primary oracle; paper-rounding tolerance is 5 us. |
| A13 | Ding-Jiang Figures 7-8 apply state depolarization to a noiseless optimal rank-one qubit strategy, giving a uniform `1/4` output term. | Active for the main-text reproduction; Appendix A.4 higher-dimensional rank-dependent strategies are excluded. |
| A14 | Ding-Jiang does not state the main Figure 7-8 grid spacing; the reproduction uses 0.01 on `[0,1]^2`. | Active; Appendix Figures 10-11 explicitly use 0.1. |
| A15 | The independent Ding loss upper-value oracle is a real-moment standard NPA `Q1+AB` relaxation, not the unpublished modified-NPA implementation cited as reference [32]. | Active; it provides a guarded numerical threshold lower bound, not a formal machine-certified proof. |
| A16 | For explicit lossy strategies, the first efficiency with detected positive advantage upper-bounds the physical `eta_star`; a lower efficiency where this optimizer found no advantage does not independently lower-bound `eta_star`. | Active; only the NPA quantum-value upper bound supplies the numerical lower side of the reported bracket. |
| A17 | Figure 5(b,c) cross-sections use increments of 0.1 because the main-text point spacing is unspecified and Appendix Figure 12 explicitly uses 0.1. | Active; the full main Figure 5(a) 101x101 surface is not claimed. |
| A18 | The Figure 5 NPA run uses CLARABEL tolerance `1e-8` with a `1e-7` objective guard and advantage classification tolerance `2e-7`. | Sensitivity checks at `1e-9`, `3e-9`, and `1e-8` gave the same selected threshold; `1e-8` avoided `optimal_inaccurate` statuses. |
| A19 | The Figure 5 explicit optimizer evaluates the full 20x20 angle grid for every fallback, then locally refines the best two starts per fallback. | This is cheaper than locally refining every grid point as Appendix B.2 may imply; thresholds are explicit-strategy upper bounds, not certified global optima. |
| A20 | Li Figure 2(a,b) uses 0.01 grids in utility and independent-input probability; panel (b) uses 0.005 in `P(1,1)`. | The paper does not publish source grids; these values resolve the displayed domains into 101 points per axis. |
| A21 | Li Figure 2(b) is normalized as `P11=t`, `P01=P10=t/2`, and `P00=1-2t` for `0<=t<=0.5`. | This is the unique normalized distribution satisfying the caption relation `P11=2P01=2P10`. |
| A22 | Li Figure 2 is `PARTIAL` at paper level even when configured gates pass. | Author pointwise numerical data are unavailable; equations, exact limits, independent classical enumeration, and visual structure are the available oracles. |
| A23 | Li Figure 3(b) uses an `epsilon` grid from 0 to 0.292 in steps of 0.001, stopping below the CHSH threshold. | The paper does not publish source grids; the endpoint resolves the displayed divergence without evaluating the no-finite-solution threshold itself. |
| A24 | The finite-statistics implementation uses `ceil(m*omega_Q)` and the strict condition `p<alpha`; an equality does not certify advantage. | This follows Li Eqs. 17, 40, and 42 exactly and is protected by boundary tests. |
| A25 | Figure 3 paper-level reproduction remains `PARTIAL` even though equation-level gates pass. | Author curve data are unavailable; the exact equations, independent Decimal points, reference lines, and qualitative divergence are the available oracles. |
