# Ding-Jiang to Li et al. Model Map

Project: Quantum Network Simulator Research and Development

Sources:

| Reference | Version | Retrieval date | Primary URL |
|---|---|---|---|
| Ding and Jiang, "Coordinating Decisions via Quantum Telepathy" | arXiv:2407.21723v3 | 2026-08-31 | https://arxiv.org/abs/2407.21723 |
| Li et al., "Operational criteria for quantum advantage in latency-constrained nonlocal games" | arXiv:2604.07451v1 | 2026-08-31 | https://arxiv.org/abs/2604.07451 |

Initial audit result (2026-08-31): the workspace was empty and was not a Git repository, so there was no prior implementation or history to inspect. Current state (2026-09-01): a fresh Git repository, scientific scaffold, validation records, and the first Layer 0/1 implementations now exist. The architecture below remains the controlling design map and gap analysis.

## Scientific Progression

| Ding-Jiang concept | Li et al. extension | Simulator implication |
|---|---|---|
| TC problem with local observations and decisions | LCTC formalized with `T_loc`, `T_comm`, and finite `T_env` | Preserve TC/nonlocal game core; add explicit timing semantics |
| HFT hedging toy model with symmetric beta | Asymmetric utility with beta1 and beta2 | Generalize utility constructor without changing Ding symmetric reproduction |
| Independent Bernoulli inputs | Arbitrary correlated `P(x,y)` | Input distribution must be a first-class config object |
| Classical value from deterministic local strategies | Same admissible classical baseline under LC condition | Shared randomness handled by convex hull, but small games use deterministic enumeration oracle |
| Quantum value from XOR SDP or explicit optimizer | Same `C(M)` and `Q(M)` feed fidelity/statistics criteria | Factor generic XOR game out as Layer 1 |
| Positive expected-utility gap | Positive gap plus fidelity, rate/statistics, and decision latency | Add explicit theoretical vs operational status |
| Type I direct photons with loss threshold | Memory-based event-ready architecture to avoid loss-as-absence problem | Keep Ding Type I/M0 separate from Li M2 memory model |
| Type II generic quantum memory rate `r_e=M p_s/t_a` | Time-multiplexed M2 model with occupancy and channel saturation | Do not silently reinterpret Ding M1 as Li M2 |
| Depolarizing noise robustness | Exact combined infidelity from state and measurement errors | Implement both Ding noise and Li combined infidelity with clear naming |

## Inheritance Boundaries

The implementation should reuse Ding-Jiang only up to the mathematical game layer and HFT utility family. It must not retrofit Li operational semantics into Ding reproduction outputs.

| Boundary | Required policy |
|---|---|
| Utility parity convention | Keep paper-specific relabeling fixtures; assert CHSH-equivalent values under relabeling |
| Classical baseline | One deterministic enumerator shared by both papers; never compare quantum to random-only |
| Quantum optimum | Shared XOR optimizer for `Q(M)`, with Ding-specific and Li-specific wrappers |
| Noise | Ding `nu` depolarizing behavior and Li combined `epsilon` are distinct models |
| Loss | Ding Type I loss `eta` and Li HEG success probability `p_ent` are distinct operational quantities |
| Memory | Ding M1 generic rate and Li M2 occupancy/time-multiplexing must be separate strategy/hardware classes |
| Advantage language | `theoretical_advantage` and `overall_operational_quantum_advantage` must both be reported |

## Layered Architecture Impact

| Layer | Required from Ding-Jiang | Required from Li et al. | Notes |
|---|---|---|---|
| Layer 0: generic nonlocal game | Definitions 1-4, Eq. A.1-A.2 | Eq. 1-4 | This is the shared foundation |
| Layer 1: XOR/generalized CHSH | HFT as XOR, Theorem 10, Tsirelson theorem | Eq. 5-14, Eq. 25, Eq. 32-36 | Must include deterministic enumeration oracle |
| Layer 2: Ding HFT/LCTC | Eq. 3.1, Fig. 3, loss/noise figures | Used as baseline in Li Fig. 2a | Freeze Ding reproduction once validated |
| Layer 3: Li generalized LCTC | Not present except symmetric beta and Bernoulli inputs | beta1/beta2, arbitrary `P(x,y)`, `T_loc`, `T_comm`, `T_env` | Add by extension, not mutation |
| Layer 4: physical-error model | Depolarizing `nu` and robustness | `epsilon_s`, `epsilon_meas`, exact `epsilon`, threshold | Exact expression is mandatory |
| Layer 5: finite statistics | Not operationally treated | Eq. 16-21 and Eq. 39-43 | Use stable binomial survival functions |
| Layer 6: decision latency | Informal local-operation comparison | Eq. 44-45 | Separate from `T_env` and `T_comm` |
| Layer 7: memory/network | Ding Type II `r_e` | M2 Eq. 46-57, Table III | Analytical model first, event simulation second |
| Layer 8: multiparty | Future work only | Eq. 62-67, Appendix B-C | Phase after bipartite validation |

## Ding to Li Gap Analysis

| Gap | Ding-Jiang status | Li et al. requirement | Implementation consequence | Priority |
|---|---|---|---|---|
| Version pinning | v3 has corrections to HFT and memory calculations | v1 currently sole Li version | Record versions and retrieval dates in configs/results | P0 |
| Repository baseline | Fresh validated implementation and regression history now exist | Regression required before Li support | Preserve Ding tests and versioned result artifacts | P0 |
| Generic game model | Defined in appendix | Used throughout | Implement core first | P1 |
| Classical optimum | Deterministic enumeration described | Same baseline | Independent oracle mandatory | P1 |
| Quantum optimum | XOR SDP and general optimizer | `Q(M)` central to criteria | Start with 2x2 XOR exact/numeric solver | P1 |
| HFT utility | Symmetric beta | beta1/beta2 asymmetric utility | Generalize while preserving Ding fixture | P2 |
| Input distribution | Independent Bernoulli | Arbitrary correlated `P(x,y)` | Config schema and validation for probability simplex | P2 |
| Fidelity | Ding qubit depolarizing robustness implemented | Exact state/measurement combined infidelity | Separate `nu` and `epsilon` modules; no approximation-only implementation | P3 |
| Finite statistics | Not central | Required for operational certification | Exact binomial tail and `n_req` search | P3 |
| Decision timing | Informal local operation speed | Formal `tau_dec < T_loc` | Operational status criterion | P4 |
| HEG rate | Generic `r_e=M p_s/t_a` | Occupancy and time multiplexing | Implement M2 analytical model | P5 |
| 50 km benchmark | 56.3 km NYSE/NASDAQ examples | Table III 50 km system-level result | Dedicated benchmark from lower-level parameters | P5 |
| Microscopic cQED | Not present | Appendix C models | Mark partial unless reconstructed and validated | P6 |
| Multiparty | Left to future work | Three-party GHZ model | Defer until two-party gates pass | P7 |

## Parameter Provenance

| Parameter | Ding-Jiang source | Li source | Simulator handling |
|---|---|---|---|
| `p` | Bernoulli indicator probability in Sec. 3 and Theorem 10 | Fig. 2a baseline and Fig. 7b multiparty Bernoulli input | Scenario config, not hardcoded |
| `beta` | Eq. 3.1 symmetric utility | Eq. 22 baseline; beta1=beta2 in Fig. 2a | Ding wrapper maps to Li symmetric case |
| `beta1`, `beta2` | Not present | Eq. 23-25 | Li generalized utility only |
| `P(x,y)` | General TC definition permits correlated inputs; HFT case uses independent Bernoulli | Arbitrary correlated distribution in Eq. 25 and Fig. 2b | Validated probability table |
| `C(M)` | Classical value `c_star` | Eq. 9 and Eq. 33 | Deterministic enumeration oracle |
| `Q(M)` | Quantum value `q_star`/XOR SDP | Eq. 32 | XOR optimizer |
| `eta` | Direct photon/loss efficiency | Not equivalent to HEG `p_ent` | Ding Type I loss model |
| `nu` | Depolarizing noise strength in Eq. 4.2-4.3; Figures 7-8 configured at 0.01, 0.05, 0.1 | Not Li `epsilon` | Ding rank-one qubit robustness only |
| `epsilon_s` | Broad physical fidelity discussion only | Eq. 26 | Li fidelity model |
| `epsilon_meas` | Broad fidelity discussion only | Eq. 28 | Li measurement model |
| `epsilon` | Not same as Ding `nu` | Eq. 30 | Li combined infidelity |
| `T_loc` | Informal reaction/local operation time | Eq. 15, 44-45 | LCTC timing config |
| `T_comm` | Informal communication latency | Eq. 15 | LCTC timing config |
| `T_env` | Not formalized | Eq. 18, Table I | Certification window config |
| `R_req` | Not formalized | Eq. 18 and Eq. 41-43 | Statistics-derived rate |
| `R_HEG` | Generic memory rate `r_e`, reproduced as `105.873 M Hz` for the v3 HFT parameters | Eq. 52 and Eq. 57 | Keep paper-specific M1 and M2 throughput implementations separate |
| `N_a`, `N_ch` | Ding has only ideal multiplicity `M`; no occupancy or channel model | Eq. 47, 52, Table III | Do not map `M` directly to M2 memory/channel capacity |

## Reproduction Target Ordering

1. CHSH analytical limits:
   - This gates all further work.

2. Ding-Jiang v3:
   - Eq. 3.1 utility.
   - Theorem 10 biased CHSH.
   - Fig. 3 ideal gap.
   - Fig. 5 loss threshold.
   - Fig. 7-Fig. 8 robustness/noisy gap.
   - Type II rate formula.

3. Li et al. v1 Fig. 2:
   - Independent Bernoulli symmetric utility.
   - Correlated input distributions.
   - Asymmetric beta cases.
   - Combined-infidelity dependence and threshold.

4. Li et al. v1 Fig. 3:
   - Exact binomial-tail `n_req`.
   - Required rate versus `epsilon`, `alpha`, `T_env`.
   - Divergence/increase near `epsilon_th`.

5. Li Table II:
   - Operational criteria map to fields in standardized output.

6. Li Table III:
   - 50 km benchmark emerges from Eq. 46-61.

7. Analytical M2 versus event-driven:
   - Only after analytical model passes Table III.

## Current Validation Gate

Current gate: Phase 8 Li analytical M2 HEG and time-multiplexing model. Phase 7 decision latency and the standardized Table II status pass strict-boundary tests.

Status:

| Gate item | Status | Notes |
|---|---|---|
| Repository structure inspected | PASS | Fresh scaffold and research documents inspected |
| Instruction docs read | PASS | No inherited `CLAUDE.md` or `AGENTS.md`; current `ROADMAP.md`, `VALIDATION.md`, and reproduction matrix reviewed |
| Git status inspected | PASS | Fresh repository initialized on `main` |
| Recent commits inspected | PASS | Fresh project history contains validated scaffold, Figure 3, loss, and Type II commits |
| Ding-Jiang version pinned | PASS | arXiv v3 confirmed |
| Li et al. version pinned | PASS | arXiv v1 confirmed; no newer revision visible when reverified 2026-09-02 |
| Ding implementation audited | PASS | No inherited code existed; current Ding utility and biased-CHSH oracle reviewed |
| Ding Type II memory calculation | PASS | Corrected v3 `t_a`, `p_s`, `r_e`, and M=1 demand conclusion reproduced |
| Ding depolarizing-noise calculation | PASS | Eq. 4.2-4.3, CHSH robustness, and configured Figure 7-8 grids validated |
| Ding loss-threshold cross-sections | PARTIAL | Figure 5(b,c), CHSH endpoint, representative threshold, and NPA/explicit bracket pass; full surface and author modified-NPA comparison unavailable |
| Li generalized LCTC and fidelity model | PASS | Correlated inputs, independent beta values, Werner state, measurement visibility, exact combined infidelity, gap, and threshold are tested |
| Li Figure 2 computation gate | PASS | 20,402 ideal points, 3,208 noisy points, and 202 threshold points pass nine configured validations |
| Li Figure 2 paper-level reproduction | PARTIAL | Visual structure and exact/invariant oracles pass; author pointwise numerical data are unavailable |
| Li finite-statistics equations | PASS | Stable exact binomial tails, discrete `n_req`, and `R_req` pass Decimal and minimality oracles |
| Li Figure 3 computation gate | PASS | 1,758 points pass ten configured validations, including paper reference-line behavior |
| Li Figure 3 paper-level reproduction | PARTIAL | Exact equations and visual structure pass; author pointwise numerical data are unavailable |
| Li decision criterion | PASS | Eq. 44 sum and strict Eq. 45 boundary are tested independently of `T_env` and `T_comm` |
| Li Table II operational status | PASS | Theoretical, fidelity, finite-statistics, rate, decision, LCTC-regime, and overall fields are separate |
| Equation-to-code map created | PARTIAL | Through Table II is linked and validated; M2 and Table III mappings remain unimplemented |
| Next implementation gate | Phase 8 | Analytical occupancy, memory, attempt-rate, and HEG-throughput formulas |
