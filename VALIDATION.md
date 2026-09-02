# Validation

Last validation run: 2026-09-03.

Command:

```bash
python3 -m pytest
```

Result:

```text
504 passed in 16.90s
```

## Passing Coverage

| Area | Evidence |
|---|---|
| CHSH analytical values | `tests/scientific/test_chsh_oracles.py` |
| Deterministic local classical enumeration | `tests/scientific/test_chsh_oracles.py` |
| CHSH fidelity threshold | `tests/scientific/test_chsh_oracles.py` |
| Ding-Jiang beta=0 biased CHSH theorem samples | `tests/scientific/test_ding_li_utilities.py` |
| Ding-Jiang anti-CHSH utility at beta=0 | `tests/scientific/test_ding_li_utilities.py` |
| Ding-Jiang Figure 3 independent classical cross-check | `tests/scientific/test_ding_fig3_reproduction.py` |
| Ding-Jiang Figure 3 beta symmetry and beta=0.5 limit | `tests/scientific/test_ding_fig3_reproduction.py` |
| Ding-Jiang Figure 3 beta=0 Theorem 10 cross-section | `tests/scientific/test_ding_fig3_reproduction.py` |
| Ding-Jiang Figure 3 101x101 experiment gate | `experiments/ding_jiang/results/fig3_v3/fig3_summary.json` |
| Ding-Jiang lossy behavior Eq. A.11 vs Bell operator Eq. A.12 | `tests/scientific/test_ding_loss_reproduction.py` |
| Ding-Jiang `p=0.3`, `beta=0.3`, `eta=0.95` lossy value | `tests/scientific/test_ding_loss_reproduction.py` |
| Ding-Jiang Section 4.1 Schmidt coefficients | `tests/scientific/test_ding_loss_reproduction.py` |
| Ding-Jiang representative threshold efficiency | `experiments/ding_jiang/results/loss_example_v3/loss_example_summary.json` |
| Ding-Jiang loss Bell functional versus direct Eq. A.11 | `tests/scientific/test_ding_loss_sdp.py` |
| Ding-Jiang NPA `Q1+AB` CHSH and no-loss XOR upper bounds | `tests/scientific/test_ding_loss_sdp.py` |
| Ding-Jiang Figure 5(b,c) numerical threshold brackets | `experiments/ding_jiang/results/fig5_cross_sections_v3/fig5_cross_sections_summary.json` |
| Ding-Jiang Type II attempt time, two-arm success probability, and rate | `tests/scientific/test_ding_type_ii_memory.py` |
| Ding-Jiang Type II Section 4.2 experiment gate | `experiments/ding_jiang/results/type_ii_memory_v3/type_ii_memory_summary.json` |
| Ding-Jiang qubit depolarizing behavior Eq. 4.2 | `tests/scientific/test_ding_noise_robustness.py` |
| Ding-Jiang noisy utility Eq. 4.3 direct behavior cross-check | `tests/scientific/test_ding_noise_robustness.py` |
| Ding-Jiang Figure 7-8 analytical and configured-grid gates | `experiments/ding_jiang/results/noise_robustness_v3/noise_robustness_summary.json` |
| Li generalized utility with beta1/beta2 | `tests/scientific/test_ding_li_utilities.py` |
| Li generalized matrix CHSH limit | `tests/scientific/test_ding_li_utilities.py` |
| Li strict latency condition | `tests/scientific/test_ding_li_utilities.py` |
| Li exact combined infidelity | `tests/scientific/test_li_fidelity.py` |
| Li noisy value/gap formulas | `tests/scientific/test_li_fidelity.py` |
| Li Werner state positivity, singlet fidelity, and direct noisy correlator trace | `tests/scientific/test_li_fidelity.py` |
| Li Figure 2 correlated-input family and deterministic classical oracle | `tests/scientific/test_li_fig2.py` |
| Li 2x2 quantum bias versus independent measurement-angle optimization | `tests/scientific/test_li_fig2.py` |
| Li Figure 2(a) full-grid Ding-layer regression | `experiments/li2026/results/fig2_v1/fig2_summary.json` |
| Li Figure 2(a-c) configured-grid analytical gates and artifacts | `tests/scientific/test_li_fig2_artifacts.py` |
| Li exact binomial tails versus independent Decimal direct sums | `tests/scientific/test_li_statistics.py` |
| Li discrete `n_req` minimality, strict alpha boundary, and no-solution cases | `tests/scientific/test_li_statistics.py` |
| Li required-rate identity and stationary-window units | `tests/scientific/test_li_statistics.py` |
| Li Eq. 20 general-score bound versus independent direct binomial sums | `tests/scientific/test_li_statistics.py` |
| Li general-score `n_req` discrete minimality | `tests/scientific/test_li_statistics.py` |
| Li Figure 3 configured-grid gates and generated artifacts | `tests/scientific/test_li_fig3_artifacts.py` |
| Li Eq. 44 decision-latency sum and strict Eq. 45 boundary | `tests/scientific/test_li_operational.py` |
| Li Table II fidelity/rate/decision status mapping | `tests/scientific/test_li_operational.py` |
| Li standardized overall status and overclaim-prevention cases | `tests/scientific/test_li_operational.py` |
| Li M2 occupancy, memory depth, and attempt rate Eqs. 46-48 versus Decimal/boundary oracles | `tests/scientific/test_li_m2_hardware.py` |
| Li memory decoherence Eq. 49 versus 60-digit Decimal exponential | `tests/scientific/test_li_m2_hardware.py` |
| Li memory-lifetime threshold Eqs. 50-51 versus independent numerical root | `tests/scientific/test_li_m2_hardware.py` |
| Li HEG rate and strict criterion Eqs. 52-53 versus Decimal/boundary oracles | `tests/scientific/test_li_m2_hardware.py` |
| Li M2-derived effective error/rate integration with operational status | `tests/scientific/test_li_m2_hardware.py` |
| Li Yb system-level Eqs. 54-61 versus independent 60-digit Decimal formulas | `tests/scientific/test_li_yb_node.py` |
| Li Table III 50 km configuration, displayed-value discrepancies, and operational cases | `tests/scientific/test_li_table3_artifacts.py` |
| Li event-driven M2 scheduling, memory limits, trace timing, and probability limits | `tests/scientific/test_li_m2_event_simulation.py` |
| Li analytical/event-driven throughput, occupancy, binomial statistics, and convergence artifacts | `tests/scientific/test_li_m2_event_artifacts.py` |
| Ding-to-Li HFT waterfall stage separation and criterion-specific failure cases | `tests/scientific/test_li_hft_waterfall.py` |
| HFT waterfall scenario oracles, score-bound minimality, and Table III source digest | `tests/scientific/test_li_hft_waterfall_artifacts.py` |

## Known Gaps

| Gap | Status |
|---|---|
| Ding-Jiang Fig. 3 paper-level numerical comparison | PARTIAL: analytical and qualitative gates pass; author numerical data is unavailable |
| Ding-Jiang full Figure 5 loss-threshold surface | PARTIAL: 0.1 cross-sections, independent NPA bounds, CHSH endpoints, and representative point pass; full 101x101 surface and author modified-NPA comparison remain unavailable |
| Ding-Jiang Type II memory-rate calculation | PASS: v3 formulas and rounded published values pass independent oracles |
| Ding-Jiang Figure 7-8 pointwise paper comparison | PARTIAL: equations, analytical extrema, symmetries, and visual shape pass; author numerical grids are unavailable |
| Li Fig. 2 reproduction | PARTIAL: all configured analytical, deterministic-enumeration, Ding-regression, and equation-consistency gates pass; author pointwise data are unavailable |
| Li finite-statistics Fig. 3 reproduction | PARTIAL: exact equations, independent Decimal points, minimality, monotonicity, divergence, and paper reference-line behavior pass; author pointwise data are unavailable |
| Li generalized bounded-score p-value, Eq. 19-21 | PASS for the published Eq. 20 upper bound: log-space interpolation, direct small-case sums, and discrete minimality pass; exact Eq. 19 score-distribution maximization is not claimed |
| Li operational output schema | PASS: all required statuses and source quantities are emitted; strict equality and partial-failure cases are tested |
| Li M2 analytical HEG/time-multiplexing model | PASS for Eqs. 46-53 and the configured deterministic-timing event simulation |
| Li Table III 50 km benchmark | PARTIAL: formula and operational gates pass, and `R_HEG=7854.545 s^-1` reproduces `7.9e3 s^-1`; exact listed-parameter calculations disagree with displayed `R0`, `p_ent`, `tau_occ`, and `p_false` |
| Analytical/event-driven cross-validation | PASS: 256 seeds, 26,368,000 trials, mean `7863.867 s^-1`, 95% CI `[7826.764,7900.970] s^-1`, analytical `7854.545 s^-1`, and all ten configured gates pass |
| HFT operational-advantage waterfall | PASS: eight configuration-driven scenarios, three overall PASS and five intended criterion-specific FAIL cases; hardware inputs are traced to the committed Table III artifact |
