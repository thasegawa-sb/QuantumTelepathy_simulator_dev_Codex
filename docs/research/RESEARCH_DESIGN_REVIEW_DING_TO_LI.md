# Research/Design Review: Ding-Jiang to Li et al. Operational LCTC Extension

Date: 2026-08-31, updated 2026-09-01

## Executive Summary

The literature path is clear. The initial workspace was empty and not a Git repository, so no prior Ding-Jiang implementation, tests, experiments, validation records, project memory, or commit history could be audited. On 2026-09-01, the user requested a fresh `git init`; a new repository and minimal scientific scaffold now exist.

The correct development sequence remains staged. The independently verified nonlocal/XOR-game core, Ding ideal HFT, representative loss case, corrected v3 Type II memory calculation, and qubit depolarizing robustness now pass their analytical gates. The full Figure 5 surface remains partial before the Li operational layers advance.

## Existing Implementation

| Area | Finding |
|---|---|
| Repository structure | Fresh scaffold |
| Source code | Shared core plus paper-specific Ding and Li modules present |
| Tests | CHSH, utility, fidelity, Figure 3, loss, Type II, and depolarizing-noise scientific tests present |
| Experiment scripts | Ding Figure 3, loss example, Type II memory, and Figure 7-8 scripts present |
| Configurations | Version-pinned Ding experiment configurations present |
| Validation results | Generated Ding result summaries and data present |
| Paper reproduction code | Ding ideal, loss, Type II, and qubit-noise reproduction paths present |
| Git history | Fresh repository initialized 2026-09-01 |
| Project memory docs | `ROADMAP.md`, `VALIDATION.md`, `ASSUMPTIONS.md`, `DECISIONS.md` added |
| Current validation gate | Phase 2 partial; full Figure 5 loss surface remains |

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
| Stable binomial-tail statistics | Still missing |
| Hardware parameter/config system | Still missing |

## Missing Components

The following are mandatory before operational Li claims:

| Component | Why required |
|---|---|
| Version-pinned result metadata | Ding v3 and Li v1 must not be mixed with earlier versions |
| Classical deterministic enumerator | Independent oracle for admissible classical baseline |
| CHSH analytical tests | PASS: gate for `C(M)`, `Q(M)`, `omega_C`, `omega_Q`, threshold |
| Ding HFT reproduction | Prevent Li extension from silently changing foundational results |
| Li generalized utility/input model | PARTIAL: supports beta1, beta2, and arbitrary 2x2 `P(x,y)` |
| Exact Li fidelity model | PASS for Eq. 30/34/37 formulas |
| Exact binomial finite-statistics model | Required for Criterion B |
| Decision-latency model | Required for Criterion C |
| M2 time-multiplexed memory model | Required for Li operational architecture |
| 50 km benchmark | Required for Table III reproduction |
| Standard operational status output | Prevent ambiguous "quantum advantage" claims |

## Required Refactoring

Because no existing implementation is visible, these are architectural requirements rather than concrete refactors:

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
| P2 | Ding loss and p=0.3, beta=0.3, eta=0.95 example | PASS for representative case; full Figure 5 remains PARTIAL |
| P2 | Ding Type II v3 memory calculation | PASS for exact formulas and rounded Section 4.2 values |
| P2 | Ding robustness/noisy-gap figures | PARTIAL: analytical and visual gates pass; author pointwise data unavailable |
| P3 | Li Eq. 23-25 generalized LCTC | PASS for utility/matrix unit tests |
| P3 | Li Fig. 2 | NOT_IMPLEMENTED |
| P4 | Li finite statistics and Fig. 3 | NOT_IMPLEMENTED |
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

1. Restore repository or explicitly scaffold a new package.
2. Add version/result metadata support.
3. Implement Layer 0 expected utility and deterministic classical enumeration.
4. Implement Layer 1 XOR matrix, CHSH oracles, and `C(M)/Q(M)`.
5. Reproduce Ding-Jiang v3 analytical and HFT baseline results.
6. Add Li beta1/beta2 and correlated input support.
7. Add Li exact fidelity model and reproduce Fig. 2.
8. Add finite-statistics certification and reproduce Fig. 3.
9. Add operational status output and timing criteria.
10. Add M2 analytical memory/HEG model and reproduce Table III.
11. Cross-validate analytical HEG against event-driven simulation if/when the simulator exists.
12. Proceed to HFT operational waterfall, multiparty extension, and optimization only after gates pass.

## Design Decision

Implementation should not proceed in the current empty workspace without a repository restoration or an explicit decision to scaffold a new project. The scientifically smallest next task after restoration is the CHSH plus deterministic-enumeration core, not the Li hardware model.
