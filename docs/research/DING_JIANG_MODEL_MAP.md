# Ding-Jiang Model Map

Project: Quantum Network Simulator Research and Development

Reference: Dawei Ding and Liang Jiang, "Coordinating Decisions via Quantum Telepathy", arXiv:2407.21723v3.

Retrieval and version audit:

| Field | Value |
|---|---|
| Selected version | arXiv:2407.21723v3 |
| arXiv version page | https://arxiv.org/abs/2407.21723 |
| PDF | https://arxiv.org/pdf/2407.21723v3 |
| arXiv HTML | https://arxiv.org/html/2407.21723v3 |
| Retrieval date | 2026-08-31 |
| Version history from arXiv | v1 submitted 2024-07-31, v2 submitted 2024-09-10, v3 submitted 2025-08-26 |
| arXiv comments relevant to reproduction | v2 corrects an HFT-example issue in v1; v3 corrects a quantum-memory calculation and makes other edits |
| Local repository state | Fresh Git repository with generic game/XOR core and initial Ding-Jiang HFT module; no inherited implementation existed |

## Scope

This document pins the Ding-Jiang model that must be reproduced before the Li et al. operational extension is claimed. The ideal HFT layer and representative direct-loss case are implemented, while full loss figures, memory-rate, and robustness reproductions remain open.

## Scientific Model

Ding-Jiang defines a tacit-coordination (TC) problem as parties making local observations and local decisions without in-round communication. The HFT case maps to a two-party binary-input, binary-output XOR utility in which decision parity corresponds to the hedge relation between two venues.

Key simulator abstractions required:

| Concept | Ding-Jiang source | Simulator object required | Current status |
|---|---|---|---|
| TC problem tuple | Appendix A, Definition 1 | Generic `TCProblem` or `NonlocalGame` with parties, observation sets, decision sets, input distribution, utility tensor | PARTIAL |
| Behavior | Appendix A, Definition 2 | Conditional probability tensor `P(d|o)` with no-signaling checks | PARTIAL |
| Deterministic classical strategy | Appendix A, Definition 3 | Local maps `f_i: O_i -> D_i`; deterministic-strategy enumerator | PASS |
| Quantum strategy | Appendix A, Definition 4 | State plus local projective measurements or equivalent correlator optimizer | PARTIAL |
| Bell operator | Appendix A, Eq. A.2 | Oracle for finite-dimensional explicit quantum optimization | NOT_IMPLEMENTED |
| Weighted utility array | Appendix A.1 | `w[o,d] = p_O(o) u[o,d]` | PARTIAL |
| Classical/quantum value and gap | Appendix A.1 | `c_star`, `q_star`, `gap = q_star - c_star` | PARTIAL |
| XOR array | Appendix A.2 | Binary-output parity game abstraction | PARTIAL |
| Lossy behavior | Appendix A.3 | Loss model combining quantum strategy with deterministic fallback | PASS for `(2,2,2)` |
| Depolarizing-noise behavior | Appendix A.4 | Noisy quantum behavior and robustness oracle | NOT_IMPLEMENTED |

## Equation and Result Mapping

| Paper item | Section | Scientific quantity | Simulator component | Parameter source | Analytical oracle | Numerical oracle | Status | Tolerance |
|---|---|---|---|---|---|---|---|---|
| HFT anti-CHSH utility matrix | Sec. 3 | Binary utility where same/opposite action parity depends on observations N/I | HFT utility constructor with beta fixed to 0 | Paper Sec. 3 | CHSH/anti-CHSH relabeling | Deterministic enumeration plus XOR quantum optimizer | PASS | Exact for utility entries |
| Eq. 3.1 | Sec. 3 | Hedging utility with beta in [0,1] for mixed-input cases | HFT utility family `u_HFT(o|x,y,beta)` | Paper Eq. 3.1 | At beta=0 recover anti-CHSH gap region | 101x101 Fig. 3 data and sections | PASS | Exact entries; analytical errors <= 2.22e-16 |
| Bernoulli input result | Sec. 3 and Appendix A.1 | For beta=0, quantum advantage iff p in `(1 - 1/sqrt(2), 1/sqrt(2))` | Independent Bernoulli input distribution | Paper Sec. 3, Theorem 10 | Theorem 10 | Grid scan over p | PASS | Boundary error <= 1e-8 |
| Eq. 4.1 | Sec. 4.1 | Example Schmidt decomposition for p=0.3, beta=0.3, eta=0.95 strategy | Explicit strategy record and validation fixture | Paper Eq. 4.1 | Schmidt singular values | Optimized lossy Bell operator | PASS | Published values within 5e-4 |
| Effective memory rate | Sec. 4.2 | `r_e = M p_s / t_a` | Ding-Jiang Type II system-level rate model | Paper Sec. 4.2 | Direct formula | Distance and multiplicity sweep | NOT_IMPLEMENTED | Relative error <= 1e-12 for formula |
| Attempt time | Sec. 4.2 | NYSE/NASDAQ half-link fiber plus free-space heralding, about 230 microseconds | Ding-Jiang memory-attempt timing model | d=56.3 km, v_f=2e8 m/s, v_s=3e8 m/s | Direct formula | Unit conversion test | NOT_IMPLEMENTED | <= 0.5 microsecond |
| Success probability | Sec. 4.2 | `p_s = p_p p_c p_d (10^(-0.1 alpha d/2))^2`, about 0.0248 | Ding-Jiang memory success model | alpha=0.17 dB/km, p_p=0.5, p_c=0.5, p_d=0.9 | Direct formula | Parameterized reproduction | NOT_IMPLEMENTED | Relative error <= 1e-3 |
| General memory rate | Sec. 4.2 | `r_e = M * 2 p_p p_c p_d 10^(-0.1 alpha d) / (d(1/v_f + 1/v_s))` | Generic two-node memory rate model | Paper Sec. 4.2 | Direct formula | Sweep over distance and M | NOT_IMPLEMENTED | Relative error <= 1e-12 |
| Depolarizing behavior | Sec. 4.2, Eq. 4.2 | Qubit strategy behavior shrinks toward uniform `1/4` | Ding-Jiang depolarizing noise model | Paper Eq. 4.2 and Appendix A.4 | Exact affine behavior | Robustness heatmap | NOT_IMPLEMENTED | <= 1e-12 |
| Noisy expected utility | Sec. 4.2, Eq. 4.3 | Expected utility maps to `(1-nu) u_bar + nu/2` for hedging qubit strategies | Ding-Jiang noisy utility model | Paper Eq. 4.3 | Exact affine expression | Fig. 8 reproduction | NOT_IMPLEMENTED | <= 1e-12 |
| Robustness | Sec. 4.2 | `nu_star = (q_star - c_star)/(q_star - 1/2)` | Ding-Jiang robustness function | Paper Sec. 4.2 | Direct formula once `c_star`, `q_star` known | Reproduce Fig. 7 | NOT_IMPLEMENTED | <= 1e-8 except near zero gap |
| Eq. A.1 | Appendix A | Expected utility for general TC behavior | Generic nonlocal game value evaluator | Definitions 1-2 | Direct finite sum | Strategy fixture tests | PASS | Exact for rational inputs |
| Eq. A.2 | Appendix A | Bell operator for explicit finite-dimensional quantum strategies | Quantum-strategy evaluator | Definition 4 | Largest eigenvalue | Cross-check against XOR SDP | NOT_IMPLEMENTED | Eigenvalue abs error <= 1e-9 |
| Theorem 10 | Appendix A.1 | Closed-form biased CHSH classical and quantum values | CHSH biased oracle | Bernoulli p | Piecewise formula | Independent enumeration and vector optimization | PASS | <= 1e-9 away from boundaries |
| Eq. A.3-A.9 | Appendix A.1 | Tsirelson/Lagrange derivation for biased CHSH | Analytical reference, not production optimizer | Bernoulli p | Piecewise formula in Theorem 10 | Optional symbolic/numeric verification | NOT_IMPLEMENTED | N/A |
| Proposition 13 | Appendix A.2 | XOR anti-array preserves gap | Relabeling invariance tests | Utility tensor | Exact invariance | Random utility relabel tests | NOT_IMPLEMENTED | <= 1e-12 |
| Theorem 14 | Appendix A.2 | Tsirelson equivalence between quantum correlations and unit vectors | Quantum XOR optimizer basis | Matrix M | Known theorem | 2x2 vector optimization | PARTIAL | <= 1e-8 |
| Eq. A.10 | Appendix A.2 | Correlator from XOR probabilities | Probability/correlator converters | Behavior tensor | Direct identity | Round-trip conversion tests | NOT_IMPLEMENTED | <= 1e-12 |
| Eq. A.11-A.12 | Appendix A.3 | Lossy behavior and lossy Bell operator with deterministic fallback | `ding_jiang.loss` | Per-party eta_i and fallback strategy | Exact loss-event mixture | Direct probability vs Bell expectation | PASS | Difference 1.11e-16 |
| Proposition 19 | Appendix A.3 | Degenerate quantum behavior is classical for (2,2,2) | Loss model simplification tests | Binary problem | Classical polytope property | Both-lost deterministic limit | PARTIAL | <= 1e-12 |
| Proposition 20 | Appendix A.3 | Qubits suffice for lossy values in `(n,2,2)` | Qubit optimizer dimension policy | Binary problem | Published proposition | Representative strategy and Schmidt values | PARTIAL | Published theorem used; no independent proof |
| Eq. A.13-A.14 | Appendix A.4 | Depolarizing noise behavior and classical factorizable term | Ding-Jiang noise module | Noise nu and projector ranks | Direct formula | Fig. 7-Fig. 8 reproduction | NOT_IMPLEMENTED | <= 1e-12 |
| Eq. B.1-B.5 | Appendix B | General-purpose projective-measurement parameterization | Optional explicit quantum optimizer | Hilbert dimensions and outcomes | Paper parameter count | Compare with XOR solver on small cases | NOT_IMPLEMENTED | Optimizer-dependent |

## Figure and Table Mapping

| Paper item | Section | Scientific meaning | Simulator artifact | Oracle | Status |
|---|---|---|---|---|---|
| Fig. 1 | Sec. 2 | TC problem schematic | Documentation figure only | Paper diagram | NOT_IMPLEMENTED |
| Fig. 2 | Sec. 3 | NYSE/NASDAQ HFT setup, distance 56.3 km | Scenario configuration | Paper distance and context | NOT_IMPLEMENTED |
| Fig. 3 | Sec. 3 | Hedging quantum advantage over p and beta | `experiments/ding_jiang/reproduce_fig3.py` | 2x2 XOR vector optimizer plus independent deterministic enumeration | PARTIAL |
| Fig. 4 | Sec. 4.1 | Direct photonic Type I architecture | Architecture docs and optional system model | Paper schematic | NOT_IMPLEMENTED |
| Fig. 5 | Sec. 4.1 | Threshold efficiency eta_star over p and beta | Loss-threshold reproduction | Representative point plus future NPA/grid oracle | PARTIAL |
| Fig. 6 | Sec. 4.2 | Quantum-memory Type II architecture | M1 memory model | Paper schematic plus rate formula | NOT_IMPLEMENTED |
| Fig. 7 | Sec. 4.2 | Robustness nu_star over p and beta | Noise robustness reproduction | Eq. 4.2-4.3 and quantum/classical values | NOT_IMPLEMENTED |
| Fig. 8 | Sec. 4.2 | Quantum advantage under depolarizing noise | Noisy HFT reproduction | Eq. 4.3 and gap calculation | NOT_IMPLEMENTED |
| Fig. 9 | Appendix B | Low-resolution Fig. 3 reproduction by general optimizer | Optimizer regression | Production-independent optimizer | NOT_IMPLEMENTED |
| Fig. 10 | Appendix B | Low-resolution robustness reproduction | Optimizer regression | Production-independent optimizer | NOT_IMPLEMENTED |
| Fig. 11 | Appendix B | Low-resolution noisy advantage reproduction | Optimizer regression | Production-independent optimizer | NOT_IMPLEMENTED |
| Fig. 12 | Appendix B | Loss threshold from general optimizer | Deterministic grid plus Powell optimizer | Representative point and limit tests | PARTIAL |
| Fig. 13 | Appendix C | Computer-architecture pseudo-example mapping to CHSH | Optional scenario fixture | Exact CHSH relabeling | NOT_IMPLEMENTED |

## Required Ding-Jiang Regression Gates

1. CHSH and anti-CHSH:
   - `omega_C = 3/4`
   - `omega_Q = (1 + 1/sqrt(2))/2`
   - `Delta omega = (sqrt(2)-1)/4`

2. Biased CHSH theorem:
   - Classical and quantum values must match Theorem 10.
   - Gap-positive interval must match `(1 - 1/sqrt(2), 1/sqrt(2))`.

3. Hedging Fig. 3:
   - Compute `Delta omega(p,beta)` for independent Bernoulli inputs.
   - Validate beta symmetry under `beta -> 1-beta`.
   - Validate zero gap at beta=0.5.

4. Loss:
   - Reproduce eta-star behavior and the p=0.3, beta=0.3, eta-star about 0.941 example.
   - Reproduce `c_star = 0.79` and `q_star(eta=0.95) approximately 0.792`.

5. Noise:
   - Reproduce affine noisy utility equation.
   - Reproduce robustness and noisy-gap figures.

6. Memory Type II:
   - Recompute NYSE/NASDAQ `t_a`, `p_s`, and `r_e`.
   - Treat Ding-Jiang Type II as M1, not the Li event-ready M2 architecture.

## Discrepancy Protocol

If reproduction disagrees with v3, investigate in this order:

1. Version mismatch with v1/v2.
2. Transcription error in utility, parity convention, or relabeling.
3. Input-distribution mismatch.
4. Classical baseline error from incomplete deterministic enumeration.
5. Quantum optimizer failure or local optimum.
6. Loss fallback strategy mismatch.
7. Unit mismatch in distance, speed, or attenuation.
8. Plot digitization uncertainty where exact data is unavailable.
9. Insufficient information.
