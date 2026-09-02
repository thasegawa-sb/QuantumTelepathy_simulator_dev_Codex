# Li et al. 2026 Model Map

Project: Quantum Network Simulator Research and Development

Reference: Changhao Li, Seigo Kikura, Akihisa Goban, Hayata Yamasaki, and Shinichi Sunami, "Operational criteria for quantum advantage in latency-constrained nonlocal games", arXiv:2604.07451v1.

Retrieval and version audit:

| Field | Value |
|---|---|
| Selected version | arXiv:2604.07451v1 |
| arXiv version page | https://arxiv.org/abs/2604.07451 |
| PDF | https://arxiv.org/pdf/2604.07451v1 |
| arXiv HTML | https://arxiv.org/html/2604.07451v1 |
| Retrieval date | 2026-08-31 |
| Version history from arXiv | v1 submitted 2026-04-08; no newer arXiv revision visible when reverified 2026-09-02 |
| Local repository state | Layer 0/1 core, Ding regression suite, Li generalized LCTC/fidelity modules, and Figure 2 experiment are present |

## Scope

Li et al. extends Ding-Jiang from idealized quantum-classical expected-utility gaps to operationally certified LCTC advantage. The simulator must keep theoretical advantage separate from operational advantage. A positive `Delta omega` is necessary but not sufficient.

## Core Layer Mapping

| Layer | Li et al. content | Required simulator component | Current status |
|---|---|---|---|
| Generic nonlocal game | Sec. II A, Eq. 1-4 | Expected utility, local/quantum behavior sets, gap | PARTIAL |
| XOR game | Sec. II A, Eq. 5-12 | Matrix `M`, correlators, `C(M)`, `Q(M)` | PARTIAL |
| LCTC timing | Sec. II B, Eq. 15 | `T_loc`, `T_comm`, LC-condition enforcement | PARTIAL |
| Finite statistics | Sec. II C, Eq. 16-21 | Exact binomial p-value, generalized score p-value bound, `n_req`, `R_req` | PASS for win/loss; general-score bound NOT_IMPLEMENTED |
| Application examples | Sec. II D, Table I | HFT, grid, load-balancing scenario configs | NOT_IMPLEMENTED |
| Generalized two-party LCTC | Sec. III A, Eq. 23-25 | Asymmetric beta1/beta2 utility and arbitrary `P(x,y)` | PASS for binary two-party scope |
| Noise/fidelity | Sec. III A-B, Eq. 26-38 | Werner state, measurement flip, combined infidelity, threshold | PASS for Figure 2 scope |
| Rate criterion | Sec. III C, Eq. 39-43 | Finite-round certification within `T_env` | PASS for CHSH/Figure 3 scope |
| Decision criterion | Sec. III D, Eq. 44-45 | `tau_dec = tau_rot + tau_meas`, compare to `T_loc` | NOT_IMPLEMENTED |
| Memory M2 architecture | Sec. IV, Eq. 46-53 | Event-ready time-multiplexed HEG, occupancy, memory threshold, channel multiplexing | NOT_IMPLEMENTED |
| Neutral-atom/Yb benchmark | Sec. V, Eq. 54-61, Table III | System-level 50 km benchmark; microscopic model optional | NOT_IMPLEMENTED |
| Multiparty extension | Sec. VI, Eq. 62-67, Appendix B | Three-party XOR/GHZ strategy, noise threshold, finite stats | NOT_IMPLEMENTED |
| cQED appendices | Appendix C, Eq. C1-C15 | Optional microscopic Bell/GHZ and measurement model | NOT_IMPLEMENTED |

## Equation Mapping

| Paper item | Section | Scientific quantity | Simulator component | Parameter source | Analytical oracle | Numerical oracle | Status | Tolerance |
|---|---|---|---|---|---|---|---|---|
| Eq. 1 | II A | Expected utility `omega` for behavior `P(a,b|x,y)` | Generic nonlocal game evaluator | `P(x,y)`, `u`, behavior tensor | Direct finite sum | Fixture behaviors | PASS | <= 1e-12 |
| Eq. 2 | II A | Local behavior with shared randomness | Classical strategy model | Shared randomness distribution | Convex hull of deterministic strategies | Enumerate deterministic strategies for binary games | PARTIAL | <= 1e-12 |
| Eq. 3 | II A | Quantum behavior from state and POVMs | Quantum strategy evaluator | State, measurements | Trace expression | Noisy singlet correlator trace | PARTIAL | <= 1e-12 for implemented singlet scope |
| Eq. 4 | II A | `Delta omega = omega_Q - omega_C` | Advantage evaluator | Values from optimizers | Direct difference | Figure 2 regression fixtures | PASS for 2x2 XOR scope | <= 1e-12 |
| Eq. 5 | II A | XOR utility depends on `a xor b` | XOR game abstraction | Binary inputs/actions | Direct parity identity | Utility conversion tests | PASS | Exact |
| Eq. 6 | II A | Correlator `E_xy` | Probability/correlator converter | Behavior tensor | Direct finite sum | Round-trip tests | NOT_IMPLEMENTED | <= 1e-12 |
| Eq. 7 | II A | XOR expected utility in correlator form | XOR evaluator | `P(x,y)`, `u(o|x,y)` | Direct identity | Compare Eq. 1 | NOT_IMPLEMENTED | <= 1e-12 |
| Eq. 8 | II A | Game matrix `M_xy = P(x,y) sum_o (-1)^o u(o|x,y)` | `GameMatrix` constructor | Utility and input distribution | Direct formula | Matrix fixture tests | PASS | <= 1e-12 |
| Eq. 9 | II A | Classical optimum `C(M)` over signs | Classical XOR optimizer | Matrix M | Enumerate all sign assignments | Independent deterministic strategy enumeration | PASS | <= 1e-12 |
| Eq. 10 | II A | Binary projective measurement from observables | Quantum measurement model | Observables A_x, B_y | Direct formula | Probability consistency tests | NOT_IMPLEMENTED | <= 1e-12 |
| Eq. 11 | II A | Correlator trace | `noisy_singlet_correlator` | State and observables | Direct density-matrix trace | Compare exact singlet dot product | PASS for singlet model | <= 1e-12 |
| Eq. 12 | II A | Normalized XOR utility `omega = (1 + sum M E)/2` | XOR value evaluator | Normalized utilities | Direct identity | CHSH benchmark | PASS | <= 1e-12 |
| Eq. 13 | II A | CHSH win utility `a xor b = x y` | CHSH fixture | Uniform inputs | Known CHSH solution | Unit tests | PASS | Exact utility |
| Eq. 14 | II A | Singlet state | `singlet_density_matrix` | Paper | Known state | Trace, fidelity, and positivity tests | PASS | <= 1e-12 |
| Eq. 15 | II B | LC condition `T_loc < T_comm` | LCTC timing validator | Scenario config | Direct inequality | Boundary tests | PASS | Exact Boolean |
| Eq. 16 | II C | Exact binomial-tail p-value for win/loss utilities | `binomial_tail_p_value` | `omega_C`, wins v, rounds m | Decimal direct binomial sum | SciPy stable survival function | PASS | <= 1e-13 small n |
| Eq. 17 | II C | Required rounds `n_req(alpha)` | `required_trials` | `omega_Q`, alpha | Exhaustive positive-integer search | Independent Decimal exhaustive search at four CHSH points | PASS | Exact integer |
| Eq. 18 | II C | Required trial rate `R_req = n_req/T_env` | `required_trial_rate` | `n_req`, `T_env` | Direct formula | Rate-times-window identity | PASS | <= 1e-9 absolute identity error |
| Eq. 19 | II C | General score p-value definition | General-score statistics | Score distribution | Optimization over classical strategies | Bound in Eq. 20 | NOT_IMPLEMENTED | PARTIAL target |
| Eq. 20-21 | II C | General-score p-value upper bound | General-score certification bound | `u_min`, `u_max`, `omega_C` | Published inequality | Monotonicity and small-case comparisons | NOT_IMPLEMENTED | Conservative bound |
| Eq. 22 | II D | Symmetric HFT utility from Ding-Jiang | HFT utility fixture | beta | Ding-Jiang Eq. 3.1 after relabeling | Full Figure 2(a) grid versus Ding layer | PASS | <= 1e-12 |
| Eq. 23 | II D | Asymmetric load-balancing/HFT-style utility with beta1/beta2 | Generalized binary XOR utility | beta1, beta2 | Direct formula | Utility symmetry/asymmetry tests | PASS | Exact entries |
| Eq. 24 | III A | Compact asymmetric XOR utility | `u_LCTC(o|x,y,beta1,beta2)` | beta1, beta2 | Direct parity formula | Compare Eq. 23 entries | PASS | Exact entries |
| Eq. 25 | III A | Matrix `M` for arbitrary `P(x,y)` and beta1/beta2; CHSH consistency fixes the right-bottom entry as `-P11` | `GameMatrix.from_lctc` | `P00,P01,P10,-P11,beta1,beta2` | Direct formula | CHSH and correlated-input fixtures | PASS | <= 1e-12 |
| Eq. 26 | III A | Werner-form entanglement infidelity `epsilon_s` | `werner_state` | `epsilon_s` | Direct density matrix | Trace, singlet fidelity, and eigenvalue tests | PASS | <= 1e-12 |
| Eq. 27 | III A | Pauli matrices | Internal quantum primitives in direct correlator | Standard matrices | Standard algebra | Exercised through arbitrary-axis trace test | PASS for required scope | <= 1e-12 |
| Eq. 28 | III A | Measurement infidelity as sign flip | `measurement_visibility` | `epsilon_meas` | Exact scaling `(1 - 2 epsilon_meas)` | Direct observable scaling test | PASS | <= 1e-12 |
| Eq. 29 | III A | Noisy singlet correlator | `noisy_singlet_correlator` | `epsilon_s`, `epsilon_meas`, unit axes | Exact density-matrix trace | Eq. 30 scaling for non-collinear axes | PASS | <= 1e-12 |
| Eq. 30 | III A | Combined infidelity `epsilon = 1 - (1 - 4 epsilon_s/3)(1 - 2 epsilon_meas)^2` | `combined_infidelity` | `epsilon_s`, `epsilon_meas` | Exact formula; approximation only secondary | Approximation-error report | PASS | <= 1e-12 exact |
| Eq. 31 | III A | Noisy quantum value `omega_Q(epsilon,M)` | Noisy XOR value | `epsilon`, `Q(M)` | Direct formula | CHSH curve | PASS | <= 1e-12 |
| Eq. 32 | III A | Quantum optimum `Q(M)` via unit vectors | Quantum XOR optimizer | Matrix M | One-dimensional Tsirelson vector reduction | Independent three-angle differential evolution | PASS for 2x2 scope | <= 1e-9 |
| Eq. 33 | III A | Classical value `omega_C(M)` | Classical XOR value | `C(M)` | Direct formula | Deterministic enumeration | PASS | <= 1e-12 |
| Eq. 34 | III A | Noisy gap `Delta omega(epsilon,M)` | Gap evaluator | `epsilon`, `C`, `Q` | Direct formula | Figure 2(c) linearity and threshold-root gates | PASS | <= 1e-12 |
| Eq. 35-36 | III A | CHSH matrix and noisy CHSH gap | CHSH oracle | Uniform inputs, beta1=beta2=0 | `C=1/2`, `Q=1/sqrt(2)` | Unit tests | PASS | <= 1e-12 |
| Eq. 37-38 | III B | Fidelity threshold and criterion | Fidelity criterion | Matrix M | `epsilon_th = 1 - C/Q` | Fig. 2 inset | PASS | <= 1e-12 except Q near 0 |
| Eq. 39-43 | III C | Rate criterion with noisy win probability | `certification_p_value`, `required_trials_sequence`, `required_trial_rate` | `epsilon`, M, alpha, `T_env`, `R_trial` | Exact binomial tail and strict inequalities | Figure 3, Decimal points, minimality/monotonicity gates | PASS | Exact n at oracle points; p <= 1e-13 |
| Eq. 44-45 | III D | Decision latency and criterion | Decision criterion | `tau_rot`, `tau_meas`, `T_loc` | Direct formula and inequality | Boundary tests | NOT_IMPLEMENTED | Exact Boolean |
| Eq. 46 | IV B | Per-qubit occupancy time | M2 memory model | `tau_e`, `tau_link`, `tau_dec`, `tau_res` | Direct sum | Table III reproduction | NOT_IMPLEMENTED | <= 1 ns for table |
| Eq. 47 | IV B | Memory depth saturation condition | M2 memory-depth validator | `N_a`, `tau_e`, `tau_occ` | Direct inequality | Boundary tests | NOT_IMPLEMENTED | Exact Boolean |
| Eq. 48 | IV B | HEG attempt rate `Gamma_HEG` | M2 throughput model | `tau_e`, `N_a`, `tau_occ` | Direct min formula | Table III reproduction | NOT_IMPLEMENTED | <= 1e-12 |
| Eq. 49 | IV B | Memory decoherence contribution to entanglement infidelity | Memory-error model | `tau_occ`, `tau_mem`, `epsilon_s` | Exact exponential formula | Small-time approximation comparison | NOT_IMPLEMENTED | <= 1e-12 exact |
| Eq. 50-51 | IV B | Memory lifetime threshold | Memory criterion | `tau_occ`, `epsilon_th`, `epsilon_meas`, `epsilon_s` | Direct formula | Limit-case tests | NOT_IMPLEMENTED | <= 1e-9 |
| Eq. 52-53 | IV B-C | HEG rate and rate criterion | M2 throughput and operational status | `N_ch`, `p_ent`, `Gamma_HEG`, `R_req` | Direct formula | Table III and Fig. 3 cross-check | NOT_IMPLEMENTED | <= 1e-12 |
| Eq. 54-55 | V B | Intrinsic HEG rate and trial period | Yb system-level model | `p_e`, `tau_p`, `tau_swap` | Direct formula | Table III `R0`, `tau_e` | NOT_IMPLEMENTED | Relative error <= 1e-3 |
| Eq. 56-57 | V C | Distance-dependent HEG success/rate | 50 km benchmark model | `eta_att`, `eta_det`, `eta_misc`, `N_ch`, M2 rates | Direct formula | Table III `R_HEG` | NOT_IMPLEMENTED | Relative error <= 1e-3 |
| Eq. 58-59 | V C | Dark-count false positives and 50 km success probability | Hardware-error model | `tau_p`, D, `p_ent` | Direct formula | Table III notes | NOT_IMPLEMENTED | Relative error <= 1e-3 |
| Eq. 60-61 | V C | Representative entanglement and combined infidelity | 50 km benchmark oracle | `epsilon_s < 0.04`, `epsilon_meas=0.002` | Eq. 30 | Recompute epsilon < 0.061 | NOT_IMPLEMENTED | Conservative inequality |
| Eq. 62-67 | VI A | Three-party majority XOR and GHZ quantum value | Multiparty extension | k=3, beta, P(x) | Known GHZ/CHSH-equivalent benchmark | Fig. 7b | NOT_IMPLEMENTED | <= 1e-8 |
| Eq. B1-B4 | App. B | Multiparty utility and correlator | Generic multiparty XOR evaluator | `P(x)`, `u(a|x)` | Direct identities | Brute-force behavior fixtures | NOT_IMPLEMENTED | <= 1e-12 |
| Eq. B5-B15 | App. B | Three-party majority XOR classical and quantum evaluation | Three-party oracle | Uniform/Bernoulli inputs | 64 deterministic strategies; GHZ angle formula | Numerical angle optimization | NOT_IMPLEMENTED | <= 1e-8 |
| Eq. B16-B22 | App. B | Three-party GHZ infidelity threshold | Multiparty fidelity module | `epsilon_GHZ`, `epsilon_meas` | Direct formula | CHSH-equivalent threshold at beta=0, uniform | NOT_IMPLEMENTED | <= 1e-12 |
| Eq. C1-C4 | App. C | TPI Bell-pair trace purity and averaged state | Optional microscopic TPI model | Temporal modes | Direct integrals where modes known | Fig. 6b if data reconstructed | NOT_IMPLEMENTED | PARTIAL target |
| Eq. C5-C6 | App. C | Measurement false-positive/false-negative probabilities | Optional microscopic measurement model | Poisson rates and lifetime | Direct Poisson/integral formulas | Fig. 6d if parameters complete | NOT_IMPLEMENTED | PARTIAL target |
| Eq. C7-C15 | App. C | CAPS GHZ reflection, postmeasurement state, fidelity | Optional microscopic GHZ model | Cavity parameters and pulse spectrum | Direct equations | Fig. 7e if data reconstructed | NOT_IMPLEMENTED | PARTIAL target |

## Figure and Table Mapping

| Paper item | Section | Scientific meaning | Simulator artifact | Oracle | Status |
|---|---|---|---|---|---|
| Fig. 1 | I-II | LCTC spacetime and timing definitions | Timing docs and scenario visualization | Paper schematic | NOT_IMPLEMENTED |
| Table I | II D | Representative `T_loc`, `T_comm`, `T_env` for HFT/grid/load balancing | Scenario defaults | Paper table | NOT_IMPLEMENTED |
| Fig. 2a | III A | Ideal gap for independent Bernoulli inputs and symmetric beta | `experiments/li2026/results/fig2_v1/fig2a_independent_gap.csv` | CHSH exact limit, all-point deterministic enumeration, Ding-layer grid | PARTIAL: configured gates PASS; no author point data |
| Fig. 2b | III A | Ideal gap for correlated inputs | `experiments/li2026/results/fig2_v1/fig2b_correlated_gap.csv` | Caption probability relation, deterministic enumeration | PARTIAL: configured gates PASS; no author point data |
| Fig. 2c | III B | Gap versus combined infidelity and threshold inset | `experiments/li2026/results/fig2_v1/fig2c_noisy_gap.csv` | Eq. 34 linearity, Eq. 37 roots, CHSH threshold | PARTIAL: configured gates PASS; no author point data |
| Fig. 3a | III C | Finite-window trial accumulation schematic | `experiments/li2026/results/fig3_v1/fig3_reproduction.png` | Paper schematic and timescale separation | PARTIAL: schematic reproduced computationally |
| Fig. 3b | III C | Required rate versus infidelity, alpha, and T_env for CHSH | `experiments/li2026/results/fig3_v1/fig3_required_rate.csv` | Exact Eq. 40-43, Decimal points, paper reference lines | PARTIAL: configured gates PASS; no author point data |
| Fig. 4 | IV | M2 time-multiplexed event-ready protocol | M2 event-ready model and optional timeline visualization | Eq. 46-53 | NOT_IMPLEMENTED |
| Table II | IV C | Mapping operational criteria to hardware requirements | Operational status schema | Paper table | NOT_IMPLEMENTED |
| Fig. 5 | V A | Telecom-band Yb node architecture | Hardware docs and optional config schema | Paper schematic | NOT_IMPLEMENTED |
| Fig. 6 | V B | Yb TPI and measurement performance | System-level oracle; microscopic optional | Eq. 54-55, Appendix C | NOT_IMPLEMENTED |
| Table III | V C | Representative 50 km benchmark | Dedicated benchmark config | Eq. 46-61 and table values | NOT_IMPLEMENTED |
| Fig. 7 | VI | Multiparty network, three-party gap, GHZ generation | Phase 12 reproduction | Eq. 62-67 and Appendix B-C | NOT_IMPLEMENTED |
| Fig. 8 | App. A | Optimal measurement angles for Fig. 2 cases | Optional strategy diagnostics | Angle optimizer | NOT_IMPLEMENTED |
| Fig. 9 | App. C | GHZ-generation schematic | Documentation and optional microscopic model | Appendix C | NOT_IMPLEMENTED |

### Figure 2 Reproduction Record

The configured v1 reproduction uses 101x101 grids for panels (a) and (b),
3,208 noisy-curve points, and 202 threshold points. Panel (a) recovers the
CHSH maximum `0.10355339059327373` at `p=0.5`, `beta=0`; panel (b) has grid
maximum `0.06742346141747668` at `P(1,1)=0.4`, `beta=0`. The CHSH fidelity
threshold is `0.2928932188134524`. All nine configured validations pass at
absolute tolerance `1e-12`.

The displayed Eq. 25 matrix prints a positive `(1,1)` entry. Direct expansion
of Eq. 24 and the CHSH matrix in Eq. 35 both require `-P(1,1)`, which is the
implemented sign. This transcription discrepancy is recorded rather than
silently choosing the displayed sign. Because no author pointwise Figure 2
data are available, the three paper-item rows remain `PARTIAL`.

### Figure 3 Reproduction Record

The configured CHSH reproduction evaluates 293 infidelities, two significance
levels, and three stationary-window durations, producing 1,758 rate points.
Independent 60-digit Decimal sums recover `n_req=34` and `143` at zero
infidelity and `n_req=65` and `238` at `epsilon=0.061`, for `alpha=0.05` and
`0.001`, respectively. The maximum configured counts at `epsilon=0.292` are
`5,083,117` and `17,946,458`, demonstrating the sharp increase near
`epsilon_th=0.2928932188134524`.

At the paper reference point `epsilon=0.061`, a `7.9 kHz` trial rate fails both
significance targets for `T_env=1 ms` but passes both for `100 ms` and `10 s`.
All ten configured validations pass. Author pointwise curve data are not
available, so Figure 3 remains `PARTIAL` at paper level.

## Operational Advantage Output Contract

The simulator should report all of the following fields, with no single overloaded "quantum advantage" flag:

| Field | PASS condition | Source |
|---|---|---|
| `latency_constrained_regime` | `T_loc < T_comm` | Eq. 15 |
| `theoretical_advantage` | `Delta omega(0,M) > 0` | Eq. 4, Eq. 34 |
| `fidelity_criterion` | `epsilon < epsilon_th(M)` | Eq. 37-38 |
| `statistical_certification` | exact or bounded p-value below alpha with planned rounds | Eq. 16-21, Eq. 40 |
| `rate_criterion` | `R_trial` or `R_HEG > n_req/T_env` | Eq. 41-43, Eq. 53 |
| `decision_criterion` | `tau_dec < T_loc` | Eq. 44-45 |
| `memory_criterion` | memory lifetime and occupancy do not push epsilon above threshold | Eq. 49-51 |
| `overall_operational_quantum_advantage` | all scientifically required criteria pass | Table II |

## Parameter Taxonomy

| Category | Parameters |
|---|---|
| Game/market | `P(x,y)`, `beta1`, `beta2`, utility family, market-correlation model |
| LCTC timing | `T_loc`, `T_comm`, `T_env` |
| Statistics | `alpha`, `omega_C`, `omega_Q`, `n_req`, `R_req` |
| Quantum strategy | `epsilon_s`, `epsilon_meas`, combined `epsilon`, `epsilon_th`, measurement axes |
| M2 network | `tau_e`, `tau_link`, `tau_dec`, `tau_res`, `tau_occ`, `N_a`, `N_ch`, `Gamma_HEG`, `p_ent`, `R_HEG` |
| Device/network | distance `L`, fiber attenuation `alpha_att`, detector efficiency `eta_det`, optics efficiency `eta_misc`, dark count rate `D`, photon pulse width `tau_p`, photon-emission probability `p_e`, memory lifetime `tau_mem` |

## Minimal Validation Gates

1. CHSH:
   - `C(M_CHSH)=1/2`
   - `Q(M_CHSH)=1/sqrt(2)`
   - `omega_C=3/4`
   - `omega_Q=(1+1/sqrt(2))/2`
   - `Delta omega=(sqrt(2)-1)/4`
   - `epsilon_th=1-1/sqrt(2)`

2. Asymmetric/correlated matrix:
   - Eq. 24 expands exactly to Eq. 23.
   - Eq. 25 reduces to CHSH matrix under uniform inputs and beta1=beta2=0, including the `-P(1,1)` right-bottom sign.

3. Finite statistics:
   - Eq. 40 exact binomial p-value agrees with direct summation for small `m`.
   - `n_req` is a minimal integer and increases as `epsilon` approaches threshold.

4. Operational status:
   - Positive theoretical gap alone never sets `overall_operational_quantum_advantage`.
   - Each criterion can fail independently in tests.

5. Table III:
   - The 50 km result must emerge from parameters:
     - `tau_e = 580 ns`
     - `tau_link = 240 us`
     - `tau_dec = 1 us`
     - `tau_occ = 244 us`
     - `p_ent(50 km) = 7.7e-3`
     - `R_HEG = 7.9e3 s^-1`
     - `epsilon < 0.061`
