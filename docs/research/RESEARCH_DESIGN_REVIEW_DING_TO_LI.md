# Research/Design Review: Ding-Jiang to Li et al. Operational LCTC Extension

Date: 2026-08-31, updated 2026-09-03

## Executive Summary

The literature path is clear. The initial workspace was empty and not a Git repository, so no prior Ding-Jiang implementation, tests, experiments, validation records, project memory, or commit history could be audited. On 2026-09-01, the user requested a fresh `git init`; a new repository and minimal scientific scaffold now exist.

The correct development sequence remains staged. The independently verified nonlocal/XOR-game core, scoped Ding baseline, Li two-party operational/hardware layers, HFT waterfall, and three-party XOR/GHZ Appendix B model now pass their configured gates. Documented paper-level partial results remain partial where author data or internally consistent displayed values are unavailable. The next gate is hardware-resource optimization.

## Existing Implementation

| Area | Finding |
|---|---|
| Repository structure | Fresh scaffold |
| Source code | Shared core, paper-specific Ding/Li modules, analytical hardware models, and event-driven M2 simulator present |
| Tests | CHSH, Ding regressions, Li utility/fidelity/statistics, Figures 2-3, operational status, hardware, and DES tests present |
| Experiment scripts | Version-pinned Ding reproductions, Li Figure 2-3/Table III scripts, and M2 cross-validation present |
| Configurations | Version-pinned Ding and Li experiment configurations present |
| Validation results | Generated Ding and Li result summaries and data present; Phase 10 statistical gates pass |
| Paper reproduction code | Scoped Ding baseline plus Li generalized LCTC, fidelity, statistics, and timing paths present |
| Git history | Fresh repository initialized 2026-09-01 |
| Project memory docs | `ROADMAP.md`, `VALIDATION.md`, `ASSUMPTIONS.md`, `DECISIONS.md` added |
| Current validation gate | Phase 13; hardware-resource optimization |

Files requested by the operating procedure were not available:

| File | Status |
|---|---|
| `CLAUDE.md` | Not present |
| `AGENTS.md` | Not present |
| `ROADMAP.md` | Present |
| `CHANGELOG.md` | Not present |
| `RESEARCH_LOG.md` | Not present |
| `DECISIONS.md` | Present |
| `ASSUMPTIONS.md` | Present |
| `VALIDATION.md` | Present |
| `BENCHMARKS.md` | Not present |
| prior `docs/research/REPRODUCTION_MATRIX.md` | Not present |

## Reusable Components

The fresh scaffold now contains these reusable components:

| Component | Reuse target |
|---|---|
| Deterministic local-strategy enumerator | Ding and Li classical baselines |
| Generic expected-utility evaluator | All TC/LCTC games |
| XOR game matrix abstraction | Ding HFT and Li generalized LCTC |
| 2x2 quantum XOR optimizer | `Q(M)`, CHSH, Fig. 2, Ding Fig. 3 |
| Li exact combined-infidelity formulas | Fidelity criterion |
| Stable binomial-tail statistics | PASS for exact win/loss utilities and Figure 3 |
| Hardware parameter/config system | Still missing |

## Operational Prerequisites

The following are mandatory before operational Li claims; rows marked PASS in
their descriptions are already available, while the remaining operational
layers still block an overall claim:

| Component | Why required |
|---|---|
| Version-pinned result metadata | PASS: Ding v3 and Li v1 are recorded in experiment configs and summaries |
| Classical deterministic enumerator | PASS for binary two-party scope: independent oracle for admissible classical baseline |
| CHSH analytical tests | PASS: gate for `C(M)`, `Q(M)`, `omega_C`, `omega_Q`, threshold |
| Ding HFT reproduction | Prevent Li extension from silently changing foundational results |
| Li generalized utility/input model | PASS for binary two-party scope, including independent and correlated Figure 2 inputs |
| Exact Li fidelity model | PASS for Eq. 26 and Eq. 28-38 Figure 2 scope |
| Exact binomial finite-statistics model | PASS for Criterion B win/loss scope |
| Decision-latency model | Required for Criterion C |
| M2 time-multiplexed memory model | Required for Li operational architecture |
| 50 km benchmark | Required for Table III reproduction |
| Standard operational status output | Prevent ambiguous "quantum advantage" claims |

## Required Refactoring

The scaffold follows these architectural requirements:

| Refactor | Rationale |
|---|---|
| Separate paper-specific wrappers from shared game core | Ding and Li share math but differ in operational interpretation |
| Keep Ding `nu` and Li `epsilon` separate | They are different noise abstractions |
| Keep Ding Type II M1 and Li M2 separate | Ding uses generic memory-rate estimate; Li models event-ready time multiplexing |
| Make parameters configuration-driven | Reproduction and sensitivity analyses require traceability |
| Introduce result metadata | Every result should record paper version, config hash/path, seed if stochastic, and retrieval version |
| Separate analytical model from event-driven simulation | Li formulas should become first oracles for later stochastic simulations |

## Reproduction Targets

| Priority | Target | Status |
|---|---|---|
| P0 | CHSH analytical limits | PASS |
| P1 | Ding Theorem 10 biased CHSH | PASS for sampled unit tests |
| P1 | Ding Eq. 3.1 HFT utility and Fig. 3 | PARTIAL: computation gates pass; no author numerical grid for pointwise comparison |
| P2 | Ding loss and p=0.3, beta=0.3, eta=0.95 example | Representative case PASS; Figure 5(b,c) configured gates PASS; full Figure 5 remains PARTIAL |
| P2 | Ding Type II v3 memory calculation | PASS for exact formulas and rounded Section 4.2 values |
| P2 | Ding robustness/noisy-gap figures | PARTIAL: analytical and visual gates pass; author pointwise data unavailable |
| P3 | Li Eq. 23-25 generalized LCTC | PASS for utility/matrix unit tests |
| P3 | Li Fig. 2 | PARTIAL: configured analytical and independent-code gates PASS; author pointwise data unavailable |
| P4 | Li finite statistics and Fig. 3 | PARTIAL: computation gate PASS; author curve data unavailable |
| P5 | Li Table II operational status mapping | PASS for supplied effective system-level parameters |
| P5 | Li M2 Eq. 46-53 | PASS for analytical timing, memory, and throughput formulas |
| P5 | Li system-level Eq. 54-57 | PARTIAL: formula gate PASS; displayed `R0` and `p_ent` discrepancies retained |
| P6 | Li Table III 50 km benchmark | PARTIAL: derived rate and operational gates PASS; four displayed-value discrepancies documented |
| P7 | Analytical M2 versus event-driven HEG | PASS for deterministic timing and independent Bernoulli herald scope |
| P8 | Multiparty Fig. 7 and Appendix B-C | PARTIAL: Figure 7(b) and Appendix B computation pass; CAPS panels (c-e) remain unimplemented |

## Test Strategy

| Test layer | Primary tests |
|---|---|
| Unit analytical | CHSH values, biased CHSH theorem, utility expansion, matrix construction |
| Unit numerical | Deterministic enumeration, quantum XOR optimizer, angle optimizer sanity checks |
| Statistical | Small-n direct binomial sums, large-n stable survival functions, `n_req` minimality |
| Operational criteria | Independent pass/fail tests for theoretical, fidelity, rate, decision, latency-regime, memory |
| Reproduction | Ding figures/results, Li Fig. 2, Li Fig. 3, Li Table III |
| Stochastic | Monte Carlo convergence and analytical/event-driven HEG cross-validation |
| Regression | Ding suite after each Li modification |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Missing repository | Cannot preserve backward compatibility or audit prior work | Restore repo before implementation or explicitly scaffold new project |
| Paper-version mismatch | Reproduction values may drift | Store version in every config/result |
| Parity/relabeling mistakes | CHSH/HFT signs can flip while values appear plausible | Use exact utility tables and relabeling tests |
| Classical baseline too weak | False quantum advantage claims | Deterministic enumeration oracle for small games |
| Quantum optimizer local optima | Underestimated `Q(M)` or false discrepancies | Start with analytical/2x2 oracles and independent optimizer checks |
| Approximation replacing exact fidelity | Incorrect threshold near boundary | Implement exact Eq. 30 first |
| Finite-statistics underflow/off-by-one | Wrong `n_req` and `R_req` | Use stable survival functions and small-n brute-force tests |
| Hardcoded Table III performance | Invalid hardware conclusion | Only table values in oracle data; output from lower-level parameters |
| Microscopic cQED underspecification | Overclaiming Fig. 6/7 reproduction | Mark microscopic model partial until fully reconstructed |

## Proposed Development Sequence

1. Completed: scaffold repository and add version/result metadata.
2. Completed: implement Layer 0/1, CHSH, and deterministic classical enumeration.
3. Completed: reproduce the scoped Ding-Jiang v3 baseline and retain documented partials.
4. Completed: add Li beta1/beta2, correlated inputs, exact fidelity, and Figure 2.
5. Completed: add exact win/loss finite-statistics certification and reproduce Figure 3.
6. Completed: add operational status output and timing criteria.
7. Completed: add M2 analytical memory/HEG model for Eqs. 46-53.
8. Completed: derive and reproduce the Table III 50 km benchmark from Eqs. 54-61.
9. Completed: cross-validate analytical HEG against event-driven simulation.
10. Completed: produce the HFT operational waterfall and identify criterion-specific bottlenecks.
11. Completed: implement the three-party XOR/GHZ game, Appendix B noise model, and Figure 7(b) computation.
12. Current: optimize minimum hardware improvements under all operational constraints.

## Design Decision

The analytical and event-driven M2 contracts are consistent within the stated deterministic-timing scope, the Phase 11 waterfall consumes that hardware result, and Phase 12 adds a separate GHZ game/noise path. Development may proceed to Phase 13 without changing the retained Table III or Figure 7(b) `PARTIAL` paper-level statuses; complete Ding, two-party Li, and multiparty regression suites remain mandatory.
