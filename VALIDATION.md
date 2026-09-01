# Validation

Last validation run: 2026-09-02.

Command:

```bash
python3 -m pytest
```

Result:

```text
330 passed in 36.62s
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

## Known Gaps

| Gap | Status |
|---|---|
| Ding-Jiang Fig. 3 paper-level numerical comparison | PARTIAL: analytical and qualitative gates pass; author numerical data is unavailable |
| Ding-Jiang full Figure 5 loss-threshold surface | PARTIAL: 0.1 cross-sections, independent NPA bounds, CHSH endpoints, and representative point pass; full 101x101 surface and author modified-NPA comparison remain unavailable |
| Ding-Jiang Type II memory-rate calculation | PASS: v3 formulas and rounded published values pass independent oracles |
| Ding-Jiang Figure 7-8 pointwise paper comparison | PARTIAL: equations, analytical extrema, symmetries, and visual shape pass; author numerical grids are unavailable |
| Li Fig. 2 reproduction | NOT_IMPLEMENTED |
| Li finite-statistics Fig. 3 reproduction | NOT_IMPLEMENTED |
| Li operational output schema | NOT_IMPLEMENTED |
| Li M2 HEG/time-multiplexing model | NOT_IMPLEMENTED |
| Li Table III 50 km benchmark | NOT_IMPLEMENTED |
| Analytical/event-driven cross-validation | NOT_IMPLEMENTED |
