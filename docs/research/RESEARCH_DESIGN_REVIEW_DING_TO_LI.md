# Research/Design Review: Ding-Jiang to Li et al. Operational LCTC Extension

Date: 2026-08-31, updated 2026-09-02

## Executive Summary

The literature path is clear. The initial workspace was empty and not a Git repository, so no prior Ding-Jiang implementation, tests, experiments, validation records, project memory, or commit history could be audited. On 2026-09-01, the user requested a fresh `git init`; a new repository and minimal scientific scaffold now exist.

The correct development sequence remains staged. The independently verified nonlocal/XOR-game core, Ding ideal HFT, loss equations and Figure 5 cross-sections, corrected v3 Type II memory calculation, and qubit depolarizing robustness now pass their configured analytical gates. The full Figure 5 surface remains a documented partial result because the paper's point data and unpublished modified-NPA implementation are unavailable; work can advance to Li Figure 2 without treating that partial result as a pass.

## Existing Implementation

| Area | Finding |
|---|---|
| Repository structure | Fresh scaffold |
| Source code | Shared core plus paper-specific Ding and Li modules present |
| Tests | CHSH, utility, fidelity, Figure 3, loss/NPA, Type II, and depolarizing-noise scientific tests present |
| Experiment scripts | Ding Figure 3, loss example, Figure 5 cross-sections, Type II memory, and Figure 7-8 scripts present |
| Configurations | Version-pinned Ding experiment configurations present |
| Validation results | Generated Ding result summaries and data present |
| Paper reproduction code | Ding ideal, loss, Type II, and qubit-noise reproduction paths present |
| Git history | Fresh repository initialized 2026-09-01 |
| Project memory docs | `ROADMAP.md`, `VALIDATION.md`, `ASSUMPTIONS.md`, `DECISIONS.md` added |
| Current validation gate | Phase 7; Li decision latency and standardized operational status |

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
| P5 | Li Table II operational status mapping | NOT_IMPLEMENTED |
| P5 | Li M2 Eq. 46-57 | NOT_IMPLEMENTED |
| P6 | Li Table III 50 km benchmark | NOT_IMPLEMENTED |
| P7 | Analytical M2 versus event-driven HEG | NOT_IMPLEMENTED |
| P8 | Multiparty Fig. 7 and Appendix B-C | NOT_IMPLEMENTED |

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
6. Current: add operational status output and timing criteria.
7. Add M2 analytical memory/HEG model and reproduce Table III.
8. Cross-validate analytical HEG against event-driven simulation.
9. Proceed to HFT waterfall, multiparty extension, and optimization only after gates pass.

## Design Decision

The Figure 3 computation gate is internally consistent and Ding regression remains mandatory. Development may proceed to Phase 7 operational timing/status; hardware modeling remains deferred until that status contract is validated.
