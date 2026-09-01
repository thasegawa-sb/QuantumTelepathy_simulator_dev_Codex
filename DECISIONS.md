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
