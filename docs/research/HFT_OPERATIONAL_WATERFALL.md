# HFT Operational-Advantage Waterfall

## Scope and Provenance

This Phase 11 analysis connects Ding-Jiang arXiv:2407.21723v3 to the
operational criteria of Li et al. arXiv:2604.07451v1. It is a prospective
system-level feasibility calculation, not observed trading performance or an
empirical market calibration.

Hardware inputs are read from
`experiments/li2026/results/table3_50km_v1/table3_summary.json`, whose SHA-256
digest in the committed run is
`da87a04fd2c11c884d79a627a1f8314bd45227f713f2e1ba54e674701b50efd0`.
The inherited values are:

| Quantity | Value |
|---|---:|
| Memory-adjusted combined infidelity | `0.060972738493541345` |
| HEG rate | `7854.545454545455 s^-1` |
| Basis rotation time | `100 ns` |
| Measurement time | `870 ns` |
| Total decision latency | `970 ns` |
| Default communication time | `240 us` |

## Stage Semantics

The seven reported stages are:

1. Ding-Jiang ideal gap.
2. Li generalized ideal gap.
3. Li gap after physical infidelity.
4. Finite-statistics certification.
5. HEG-rate feasibility within `T_env`.
6. Local decision-latency feasibility.
7. Overall feasibility, including strict `T_loc<T_comm`.

Stage 1 to stage 2 is a model transition when the input distribution or utility
changes. It is not a physical degradation term. The physical retained fraction
is therefore calculated only between stages 2 and 3.

Binary win/loss utilities use the exact Li Eq. 16 binomial tail. Fractional
utilities use the conservative Eq. 20 interpolated binomial upper bound. Both
paths use `ceil(m*omega_Q)` and strict `p<alpha`; rate, fidelity, decision, and
communication boundaries are also strict.

For a failing scenario, the bottleneck is the first failed criterion in stage
order. For a passing scenario, it is the criterion with the smallest
dimensionless headroom relative to its strict boundary.

## Configured Results

| Scenario | Ding ideal gap | Li ideal gap | Noisy gap | Statistics | `n_req` | `R_req (s^-1)` | Overall | Dominant/failed bottleneck |
|---|---:|---:|---:|---|---:|---:|---|---|
| `uniform_chsh_reference` | 0.103553391 | 0.103553391 | 0.0819962722 | exact binomial | 65 | 65 | PASS | fidelity criterion |
| `ding_representative_10s` | 0.0223395588 | 0.0223395588 | 0.00329536057 | general-score bound | 66133 | 6613.3 | PASS | fidelity criterion |
| `ding_representative_1s_rate_limited` | 0.0223395588 | 0.0223395588 | 0.00329536057 | general-score bound | 66133 | 66133 | FAIL | rate criterion |
| `correlated_asymmetric_generalized` | 0.0863406012 | 0.0403966007 | 0.0190319604 | general-score bound | 1772 | 1772 | PASS | fidelity criterion |
| `correlated_asymmetric_fidelity_limited` | 0.0701562119 | 0.00412057651 | -0.0183857159 | general-score bound | N/A | N/A | FAIL | fidelity criterion |
| `decision_latency_limited` | 0.103553391 | 0.103553391 | 0.0819962722 | exact binomial | 65 | 65 | FAIL | decision criterion |
| `utility_flat_limit` | 0 | 0 | -0.0152431846 | general-score bound | N/A | N/A | FAIL | theoretical advantage |
| `communication_regime_invalid` | 0.103553391 | 0.103553391 | 0.0819962722 | exact binomial | 65 | 65 | FAIL | latency-constrained regime |

Three scenarios pass all required criteria. The paired Ding representative
cases isolate the stationary-window bottleneck: identical game and hardware
parameters pass at `T_env=10 s` and fail at `T_env=1 s`. The correlated
asymmetric passing case uses
`P=((0.2,0.2),(0.2,0.4))`, `beta1=0.05`, and `beta2=0.1`.

## Validation

The classical value of every scenario is independently checked by enumerating
all 16 deterministic local strategies. The maximum discrepancy is
`1.11e-16`. Symmetric independent cases agree with the unchanged Ding layer to
`1.11e-16`. General-score required counts pass discrete minimality checks, and
all eight expected overall statuses and bottlenecks match the versioned oracle.
The full repository suite passes with 504 tests.

## Limitations

- The asymmetric `beta1 != beta2` cases are HFT-style applications of Li Eq.
  23. Li introduces that equation for load balancing, so these cases are an
  explicit research extension rather than a paper reproduction.
- No scenario is calibrated to order-book data, transaction costs, fill
  probabilities, adverse selection, or regulatory constraints.
- `statistical_certification=PASS` is prospective at the expected quantum
  score. An observed deployment requires a p-value from realized scores.
- The Eq. 20 result is an upper bound on Eq. 19's classical score probability;
  exact score-distribution maximization is not claimed.
- Hardware conclusions inherit the documented Table III `PARTIAL` paper-level
  status and its four displayed-value discrepancies.

## Artifacts

- Configuration: `experiments/li2026/configs/hft_waterfall_v1.json`
- Oracle: `experiments/li2026/oracles/hft_waterfall_v1.json`
- Summary: `experiments/li2026/results/hft_waterfall_v1/hft_waterfall_summary.json`
- Scenario table: `experiments/li2026/results/hft_waterfall_v1/hft_waterfall_scenarios.csv`
- Stage table: `experiments/li2026/results/hft_waterfall_v1/hft_waterfall_stages.csv`
- Figure: `experiments/li2026/results/hft_waterfall_v1/hft_waterfall.png`
