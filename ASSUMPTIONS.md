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
