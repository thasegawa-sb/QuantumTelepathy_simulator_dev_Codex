# Li 2026 Implementation Plan

This plan records the staged implementation after the user authorized a fresh repository. Phases 0-5 are complete at their configured gates; Phase 6 is current.

Primary references:

| Reference | Version | Retrieval date |
|---|---|---|
| Ding and Jiang, arXiv:2407.21723 | v3 | 2026-08-31 |
| Li et al., arXiv:2604.07451 | v1 | 2026-08-31 |

## Current Gate

| Item | State |
|---|---|
| Repository and traceability files | Present on `main` |
| Ding-Jiang regression baseline | Implemented; documented partials retained where author data are unavailable |
| Li generalized LCTC and Figure 2 | Configured validation gate PASS; paper reproduction PARTIAL |
| Next task | Phase 6 exact finite statistics and Figure 3 |

## Proposed Package Structure

The repository uses the following package structure:

| Proposed path | Purpose |
|---|---|
| `src/quantum_telepathy/core/nonlocal_game.py` | Generic expected utility, behavior validation, utility tensors |
| `src/quantum_telepathy/core/classical.py` | Deterministic local strategy enumeration and classical values |
| `src/quantum_telepathy/core/xor_game.py` | XOR utilities, matrix M, C(M), Q(M), CHSH oracles |
| `src/quantum_telepathy/ding_jiang/hft.py` | Ding-Jiang v3 HFT utility, Bernoulli inputs, reproduction fixtures |
| `src/quantum_telepathy/ding_jiang/loss.py` | Type I lossy behavior and eta-star |
| `src/quantum_telepathy/ding_jiang/noise.py` | Ding depolarizing `nu` robustness |
| `src/quantum_telepathy/li2026/lctc.py` | beta1/beta2 utility, arbitrary `P(x,y)`, `T_loc/T_comm/T_env` |
| `src/quantum_telepathy/li2026/fidelity.py` | `epsilon_s`, `epsilon_meas`, combined `epsilon`, `epsilon_th` |
| `src/quantum_telepathy/li2026/statistics.py` | Binomial p-values, `n_req`, `R_req`, score-bound p-values |
| `src/quantum_telepathy/li2026/operational.py` | Standard pass/fail status object |
| `src/quantum_telepathy/hardware/memory_m0_m1_m2.py` | M0 no memory, M1 generic memory, M2 event-ready time multiplexing |
| `src/quantum_telepathy/hardware/heg.py` | System-level HEG formulas |
| `src/quantum_telepathy/hardware/yb_node.py` | Li Table III system-level neutral-atom benchmark |
| `src/quantum_telepathy/multiparty/xor.py` | Three-party XOR/GHZ support after two-party gates |
| `experiments/ding_jiang/` | Ding reproduction scripts/configs |
| `experiments/li2026/` | Li reproduction scripts/configs |
| `tests/scientific/` | Analytical and reproduction tests |

## Phase Sequence

### Phase 0: Repository and Literature Audit

Status: complete.

Actions completed in this pass:

| Action | Result |
|---|---|
| Inspect workspace | Fresh scaffold created after user authorization |
| Inspect Git status | Repository initialized on `main` |
| Inspect recent commits | Validation work committed incrementally |
| Pin Ding-Jiang version | v3 confirmed |
| Pin Li version | v1 confirmed |
| Read primary papers | Paper text and appendices reviewed from arXiv HTML/PDF extraction |
| Create model-map docs | Created in `docs/research/` |

Exit conditions are recorded in `VALIDATION.md` and `REPRODUCTION_MATRIX.md`.

### Phase 1: Ding-Jiang Version-Pinned Specification

Deliverables:

| Deliverable | Acceptance criteria |
|---|---|
| Ding HFT utility specification | Eq. 3.1 represented exactly; parity/relabeling documented |
| Bernoulli input specification | Independent Bernoulli p implemented with probability normalization tests |
| Theorem 10 oracle | Closed-form biased CHSH values implemented and unit-tested |
| Ding Type I/Type II specs | Loss and generic memory-rate quantities separated from Li M2 |

Do not implement Li-specific criteria during this phase.

### Phase 2: Ding-Jiang Reference Reproduction

Deliverables:

| Target | Acceptance criteria |
|---|---|
| CHSH/anti-CHSH | Analytical values pass to tight tolerance |
| Ding Fig. 3 | Gap heatmap and cross-sections generated from solver |
| Ding Fig. 5 | PARTIAL recorded: cross-sections and independent numerical bounds pass; full surface and author modified-NPA comparison unavailable |
| Ding p=0.3, beta=0.3 example | `eta_star approx 0.941`, `c_star=0.79`, `q_star(eta=0.95) approx 0.792` reproduced or discrepancy documented |
| Ding Fig. 7-Fig. 8 | Robustness/noisy gap reproduced |
| Ding memory rate | `t_a`, `p_s`, `r_e` reproduced from v3 |

Regression policy:

| Rule | Implementation requirement |
|---|---|
| Do not silently change Ding results | Versioned fixtures and test snapshots |
| Do not update expected values casually | Use discrepancy protocol |
| Preserve paper version | Include v3 in result metadata |

### Phase 3: Generic Nonlocal/XOR Abstraction

Implement only the shared model required by Ding and Li:

| Component | Core functions |
|---|---|
| Generic game | `expected_utility(Pxy, utility, behavior)` |
| Classical oracle | deterministic local strategy enumeration |
| XOR game | matrix M, correlator conversion, `C(M)` |
| Quantum XOR | `Q(M)` for 2x2 matrices; use stable optimization or closed form where valid |
| CHSH fixture | canonical values and threshold |

Validation:

| Test | Oracle |
|---|---|
| Shared randomness baseline | Deterministic convex hull optimum |
| CHSH values | Analytical values |
| Utility normalization | Eq. 12 identity |
| Ding anti-CHSH relabeling | Gap invariance |

### Phase 4: Li Generalized LCTC Model

Status: complete for binary two-party Figure 2 scope.

Implement:

| Feature | Source |
|---|---|
| beta1/beta2 utility | Eq. 23-24 |
| arbitrary correlated `P(x,y)` | Eq. 25 |
| `T_loc`, `T_comm`, `T_env` | Sec. II B-C |
| LC validation | Eq. 15 |

Validation:

| Test | Oracle |
|---|---|
| Eq. 24 equals Eq. 23 | Exact table comparison |
| Uniform beta1=beta2=0 | CHSH matrix Eq. 35, including the negative right-bottom matrix entry |
| beta1=beta2=beta and independent Bernoulli | Ding Fig. 3/Fig. 2a baseline |
| Invalid `P(x,y)` | Probability simplex validation |

### Phase 5: Li Fidelity/Noise Model

Status: configured validation gate A PASS; paper-level Figure 2 status PARTIAL because author numerical grids are unavailable.

Implement:

| Feature | Source |
|---|---|
| Werner state infidelity | Eq. 26 |
| Measurement infidelity | Eq. 28 |
| Combined infidelity exact expression | Eq. 30 |
| Quantum value under noise | Eq. 31 |
| Gap under noise | Eq. 34 |
| Fidelity threshold | Eq. 37-38 |

Validation Gate A:

| Target | Oracle |
|---|---|
| CHSH threshold | `epsilon_th = 1 - 1/sqrt(2)` |
| Fig. 2a | independent Bernoulli symmetric utility |
| Fig. 2b | correlated inputs from caption |
| Fig. 2c | gap decreases linearly in `epsilon`; threshold inset |

### Phase 6: Finite Statistics Model

Status: current implementation gate.

Implement:

| Feature | Source |
|---|---|
| Exact binomial-tail p-value | Eq. 16 and Eq. 40 |
| `n_req(epsilon,M,alpha)` | Eq. 42 |
| `R_req` | Eq. 41 and Eq. 43 |
| General-score bound | Eq. 19-21, after win/loss support |

Numerical requirements:

| Requirement | Rationale |
|---|---|
| Use survival-function or log-space implementation for large n | Avoid underflow |
| Direct summation for small n test oracle | Independent verification |
| Minimality check for `n_req` | Prevent off-by-one errors |
| Monotonicity tests | Required rate should increase as `epsilon` approaches threshold |

Validation Gate B:

| Target | Oracle |
|---|---|
| Fig. 3b | Li CHSH required-rate curves |
| Small-n p-values | Brute-force/direct summation |
| Divergence near threshold | Qualitative and numerical monotonic behavior |

### Phase 7: Operational Timing Model

Implement:

| Feature | Source |
|---|---|
| `tau_dec = tau_rot + tau_meas` | Eq. 44 |
| Decision criterion | Eq. 45 |
| `T_loc < T_comm` enforcement | Eq. 15 |

Validation:

| Test | Oracle |
|---|---|
| Boundary cases | Strict inequalities fail on equality |
| Timescale separation | `T_env` never used as local decision deadline |
| Table I scenarios | Config-level examples |

### Phase 8: Event-Ready Time-Multiplexed Network

Implement M0/M1/M2:

| Model | Meaning | Required support |
|---|---|---|
| M0 | No quantum memory/direct resources | Type I loss as separate model |
| M1 | Ding generic quantum memory | `r_e = M p_s/t_a` |
| M2 | Li event-ready time-multiplexed memory | Eq. 46-53 |

Validation:

| Target | Oracle |
|---|---|
| Occupancy time | Eq. 46 |
| Saturation condition | Eq. 47 |
| Attempt rate | Eq. 48 |
| Memory-induced error | Eq. 49 |
| Memory lifetime threshold | Eq. 50-51 |
| HEG rate | Eq. 52 |

### Phase 9: Li 50 km Hardware Benchmark

Implement dedicated config:

| Quantity | Paper value |
|---|---|
| `C_in` | 20 |
| `N_a` | 250 |
| `tau_rot`, `tau_swap` | 100 ns |
| `tau_res` | 1 us |
| `tau_mem` | 7.9 s |
| `p_e` | 0.70 |
| TPI success probability | 0.25 |
| `tau_p` | 240 ns |
| `R0` | 4.3e5 s^-1 |
| `L` | 50 km |
| `eta_att` | 0.06 |
| `eta_det` | 0.9 |
| `eta_misc` | 0.8 |
| `tau_link` | 240 us |
| `R_HEG` | 7.9e3 s^-1 |
| `tau_e` | 580 ns |
| `tau_meas` | 870 ns |
| `tau_dec` | 1 us |
| `tau_occ` | 244 us |
| `epsilon_s` | < 4% |
| `epsilon_meas` | 0.2% |
| combined `epsilon` | < 6.1% |

Validation Gate C:

| Rule | Requirement |
|---|---|
| No hardcoded final performance | `R_HEG`, `tau_occ`, `epsilon` emerge from parameters |
| Formula-derived values | Relative error <= 1e-3 unless table uses rounded values |
| Criteria | Decision, fidelity, and rate PASS conditions reproduced under stated assumptions |

### Phase 10: Analytical/Event-Driven Cross-Validation

Only after analytical M2 passes:

| Comparison | Requirement |
|---|---|
| Analytical `R_HEG` vs event-driven Bell-pair throughput | Report seed, sample size, mean, std, CI |
| Memory occupancy distribution | Compare simulated occupancy to Eq. 46 assumptions |
| HEG attempts | Bernoulli/binomial convergence to `p_ent Gamma_HEG` |
| Discrepancies | Investigate before proceeding |

### Phase 11 and Beyond

| Phase | Scope | Gate |
|---|---|---|
| HFT operational waterfall | Ding ideal -> Li generalized -> infidelity -> finite stats -> HEG -> decision latency | Two-party gates A-C |
| Multiparty extension | Three-party XOR/GHZ, Eq. 62-67, Appendix B | Two-party cross-validation |
| Hardware optimization | Minimum improvements satisfying all criteria | Full operational status |
| HPC optimization | Performance only after correctness | Reproduction suite stable |

## Test Oracle Plan

| Oracle | Source | Test type |
|---|---|---|
| CHSH analytical results | Li Eq. 13-14, 35-36 | Unit |
| Ding biased CHSH | Ding Theorem 10 | Unit |
| Ding HFT published values | Ding Sec. 4.1 | Reproduction |
| Li fidelity formulas | Li Eq. 26-38 | Unit |
| Li finite statistics | Li Eq. 16-18, 40-43 | Unit/reproduction |
| Li hardware results | Li Table III | Reproduction |
| Deterministic enumeration | Independent implementation | Unit |
| Analytical HEG vs event-driven | Li Eq. 46-57 | Cross-validation |
| Monte Carlo convergence | Simulation statistics | Stochastic validation |
| Limit cases | p=0/1, beta=0.5, epsilon=0, threshold equality | Unit |

## Development Rule

The next scientifically meaningful action is the exact binomial finite-statistics model, including stable tails, direct small-`n` oracles, minimality tests for `n_req`, and Figure 3 reproduction.
