# Decisions

| Date | Decision | Rationale |
|---|---|---|
| 2026-09-01 | Initialize a fresh Git repository in the workspace. | User confirmed no Git repository existed and requested `git init`. |
| 2026-09-01 | Implement the smallest scientific core before Li operational layers. | CHSH and deterministic classical baselines are mandatory gates for both Ding-Jiang and Li et al. |
| 2026-09-01 | Keep Ding-Jiang and Li et al. wrappers separate while sharing the XOR core. | Prevents Li operational semantics from silently changing Ding reproduction results. |
| 2026-09-01 | Implement Li combined infidelity using the exact expression from Eq. 30. | The small-error approximation is not acceptable as the reference model. |
| 2026-09-01 | Treat microscopic cQED reproduction as deferred. | Li Table III system-level formulas are sufficient for the mandatory next hardware gate; appendix-level microscopic reproduction may require more data. |
| 2026-09-01 | Report the Ding Figure 3 computation gate as PASS but the paper-plot reproduction as PARTIAL. | Exact analytical checks pass, while author source data for nonzero beta is unavailable. |
| 2026-09-01 | Implement photon loss both as an Eq. A.11 probability mixture and an Eq. A.12 Bell operator. | The two paths provide an independent numerical cross-check of the loss semantics. |
| 2026-09-01 | Use a deterministic angle grid, Powell refinement, and all 16 fallback strategies. | Matches Appendix B.3 without stochastic optimizer variance. |
| 2026-09-01 | Represent the Ding-Jiang Type II calculation as a paper-specific M1 model with decomposed timing and two-arm transmission terms. | Preserves the corrected v3 formula and prevents accidental reuse as Li's occupancy-aware M2 model. |
| 2026-09-01 | Validate Type II against both exact formula-derived Decimal values and separately rounded publication values. | The published `230 us`, `0.0248`, and `106 Hz` have different stated precision from the underlying formulas. |
| 2026-09-01 | Implement Ding depolarizing `nu` in a paper-specific module rather than reuse Li fidelity code. | Ding Eq. 4.2 is a state-depolarizing qubit behavior; Li `epsilon` combines state and measurement infidelity under a different model. |
| 2026-09-01 | Preserve signed noisy gaps in Figure 8 data and clip only visualized surfaces at zero. | Negative values establish failure of theoretical advantage and must remain available for falsification. |
| 2026-09-02 | Bound Ding Figure 5 thresholds from both sides using explicit qubit strategies and an independent NPA `Q1+AB` relaxation. | A production strategy optimizer cannot serve as its own global-optimality oracle. |
| 2026-09-02 | Keep Figure 5 reproduction `PARTIAL` after scalar and cross-section gates pass. | Author pointwise data and the cited unpublished modified-NPA implementation are unavailable; the full 101x101 surface was not run. |
| 2026-09-02 | Use the NPA result for the exact CHSH `2/3` endpoint gate and report explicit-strategy endpoint excess separately. | Near `2/3`, positive utility gain approaches machine precision and an explicit optimizer's detection threshold is resolution-sensitive. |
| 2026-09-02 | Label the NPA objective allowance as a solver error margin, not a certification margin. | Adding a numerical margin to a solver result does not create a formal SDP certificate. |
| 2026-09-02 | Implement Li Eq. 26 and Eq. 28-29 as a density-matrix trace oracle in addition to the closed-form Eq. 30 path. | The exact combined-infidelity formula must be checked against an independently evaluated physical state and observables. |
| 2026-09-02 | Interpret Li Figure 2(b)'s caption relation with `P00=1-2P11` and retain the Eq. 24/35-consistent negative `(1,1)` matrix sign. | This preserves probability normalization and the canonical CHSH limit despite the positive sign printed in the displayed Eq. 25 matrix. |
| 2026-09-02 | Mark Li Figure 2 computation gates `PASS` but paper-level reproduction `PARTIAL`. | No author pointwise data are available for direct numerical comparison; analytical and independent-code oracles do pass. |
