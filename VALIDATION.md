# Validation

Last validation run: 2026-09-01.

Command:

```bash
python3 -m pytest
```

Result:

```text
23 passed in 0.07s
```

## Passing Coverage

| Area | Evidence |
|---|---|
| CHSH analytical values | `tests/scientific/test_chsh_oracles.py` |
| Deterministic local classical enumeration | `tests/scientific/test_chsh_oracles.py` |
| CHSH fidelity threshold | `tests/scientific/test_chsh_oracles.py` |
| Ding-Jiang beta=0 biased CHSH theorem samples | `tests/scientific/test_ding_li_utilities.py` |
| Ding-Jiang anti-CHSH utility at beta=0 | `tests/scientific/test_ding_li_utilities.py` |
| Li generalized utility with beta1/beta2 | `tests/scientific/test_ding_li_utilities.py` |
| Li generalized matrix CHSH limit | `tests/scientific/test_ding_li_utilities.py` |
| Li strict latency condition | `tests/scientific/test_ding_li_utilities.py` |
| Li exact combined infidelity | `tests/scientific/test_li_fidelity.py` |
| Li noisy value/gap formulas | `tests/scientific/test_li_fidelity.py` |

## Known Gaps

| Gap | Status |
|---|---|
| Ding-Jiang Fig. 3 reproduction | NOT_IMPLEMENTED |
| Ding-Jiang loss threshold and robustness reproductions | NOT_IMPLEMENTED |
| Li Fig. 2 reproduction | NOT_IMPLEMENTED |
| Li finite-statistics Fig. 3 reproduction | NOT_IMPLEMENTED |
| Li operational output schema | NOT_IMPLEMENTED |
| Li M2 HEG/time-multiplexing model | NOT_IMPLEMENTED |
| Li Table III 50 km benchmark | NOT_IMPLEMENTED |
| Analytical/event-driven cross-validation | NOT_IMPLEMENTED |
