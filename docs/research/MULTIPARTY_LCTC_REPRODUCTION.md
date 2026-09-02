# Multiparty LCTC Reproduction

## Scope

This Phase 12 record covers Li et al. arXiv:2604.07451v1 Section VI.A,
Figure 7(b), and Appendix B. It implements the three-party majority XOR game,
local classical benchmark, GHZ-equatorial strategy, state and measurement
errors, finite-statistics certification, and prospective operational status.

Figure 7(c-e) uses a distinct cavity-assisted photon-scattering (CAPS) protocol.
Its atom-cavity pulse dynamics and lower-level GHZ rate/fidelity calculation are
not implemented here and are not replaced by the bipartite TPI/Table III model.

## Mathematical Mapping

| Paper item | Implementation | Validation |
|---|---|---|
| Eqs. 62-65 | Three-party majority and softened parity utility | Exact utility entries and limit tests |
| Eqs. 66-67 | GHZ-equatorial quantum value and coefficients | Canonical angles and unrestricted phase optimizer |
| Eqs. B1-B4 | Generic multiparty XOR expected-utility reduction | Parity coefficients and utility enumeration |
| Eqs. B5-B15 | Three-party classical/GHZ values | 64 local strategies and stationary polynomial |
| Eq. B16 | GHZ state-infidelity density matrix | Trace, spectrum, and GHZ fidelity |
| Eqs. B17-B18 | Noisy correlator and combined infidelity | Independent 8 by 8 density-matrix trace |
| Eqs. B19-B22 | Noisy value, gap, and threshold | Canonical `1-1/sqrt(2)` oracle |
| Eq. 16 applied to Eq. 65 | Exact finite-round certification | Discrete `n_req` minimality |

The generic local strategy layer supports an arbitrary number of parties with
binary inputs and outputs. For three parties it enumerates `4^3=64`
deterministic local maps. Shared randomness cannot improve this maximum because
the local set is their convex hull.

For the permutation-symmetric IID Figure 7(b) family, the GHZ objective is a
symmetric multi-affine polynomial. The production solver reduces its maximum
modulus to the diagonal unit circle and evaluates all stationary phases of the
resulting trigonometric polynomial. A separate unrestricted three-phase
differential-evolution implementation is used only as a numerical oracle.

## Figure 7(b) Result

The configured grid contains 101 values each for Bernoulli probability `p` and
softness `beta`, for 10,201 total points.

| Quantity | Simulator result |
|---|---:|
| Maximum location | `p=0.5`, `beta=0` |
| Classical value at maximum | `0.75` |
| GHZ quantum value at maximum | `0.8535533905932737` |
| Maximum gap | `0.10355339059327373` |
| Points with displayed gap at least `10^-4` | `3474` |
| Full-grid classical-oracle maximum error | `4.44e-16` |
| Ten-point unrestricted-phase maximum error | `6.52e-13` |
| `p` reflection-symmetry error | `2.22e-16` |
| Minimum signed gap | `-2.22e-16` numerical floor |

The gap vanishes at `p=0`, `p=1`, and `beta=0.5` to the configured tolerance.
No positive gap above tolerance occurs for `beta>=0.5`, matching the region
described in Section VI.A and displayed in Figure 7(b).

## Noise and Certification

For `epsilon_GHZ=0.05` and `epsilon_meas=0.01`, Eq. B18 gives effective
infidelity `epsilon'=0.1125904`. The canonical threshold from Eq. B22 is
`0.2928932188134524`, so the noisy gap remains positive.

Li Section VI.B explicitly assigns the exact Eq. 16 binomial p-value to the
Eq. 65 utility. At `alpha=0.05`, the representative case requires
`n_req=107`; the p-value at 107 rounds is `0.048988437416019624`, while 106
rounds do not pass. For `T_env=1 s`, `R_req=107 s^-1`.

The configured `R_GHZ=10^6 s^-1` is a supplied qualitative scale from the
paper's Figure 7(e) discussion. It makes the prospective rate criterion pass,
but it does not constitute a reproduction of the CAPS hardware calculation.

## Status

| Scope | Status | Reason |
|---|---|---|
| Eqs. 62-67 game calculation | PASS | Analytical and independent numerical gates pass |
| Appendix B classical/GHZ/noise calculation | PASS | Independent strategy, phase, and density-matrix paths pass |
| Figure 7(b) computation | PASS | Complete configured grid and invariants pass |
| Figure 7(b) paper reproduction | PARTIAL | Author pointwise numerical data are unavailable |
| Figure 7(c-d) protocol representation | NOT_IMPLEMENTED | Schematic protocol is not required for game calculation |
| Figure 7(e) CAPS rate/fidelity | NOT_IMPLEMENTED | Microscopic pulse and cavity model remains separate |

## Artifacts

- Configuration: `experiments/li2026/configs/fig7b_v1.json`
- Oracle: `experiments/li2026/oracles/fig7b_v1.json`
- Grid: `experiments/li2026/results/fig7b_v1/fig7b_gap.csv`
- Quantum cross-check: `experiments/li2026/results/fig7b_v1/fig7b_quantum_cross_validation.csv`
- Figure: `experiments/li2026/results/fig7b_v1/fig7b_reproduction.png`
- Summary: `experiments/li2026/results/fig7b_v1/fig7b_summary.json`
