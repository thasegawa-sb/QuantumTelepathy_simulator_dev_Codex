# Phase 15 Final Validation

Validation ID: `phase15_v1`

Execution date: 2026-09-03 (Asia/Tokyo)

Primary references:

- Ding and Jiang, arXiv:2407.21723v3.
- Li et al., arXiv:2604.07451v1.

## Result

Phase 15 status: **PASS**.

The configuration-driven final-validation runner regenerated all 12 selected
paper-reproduction and research-extension summaries in temporary directories.
Every scientific field matched its committed oracle within an absolute
tolerance of `1e-7`. Runtime, generation timestamps, and the recorded source
path for the reused explicit Figure 5 strategy were excluded from numerical
comparison because they are execution metadata rather than scientific output.

| Validation | Result |
|---|---:|
| Reproduction and extension jobs | 12/12 PASS |
| Existing test suite executed by the runner | 592 passed |
| Phase 15 artifact tests | 3 passed |
| Audited committed result files | 45 |
| Result-artifact aggregate SHA-256 | `efcdb1d91de1a757007203c0234cdefa1b3d4568996c39bc206486f4ccc84e9a` |
| Reproduction-matrix rows | 56 |
| Reproduction-matrix vocabulary/shape audit | PASS |
| Committed artifacts unchanged by rerun | PASS |

The machine-readable result is
`experiments/final_validation/results/phase15_v1/final_validation_summary.json`.
The executable configuration is
`experiments/final_validation/configs/phase15_v1.json`.

## Scope

The final gate covers the Ding-Jiang Figure 3, representative lossy case,
Figure 5 cross-sections, corrected v3 Type II memory calculation, and noise
robustness; Li et al. Figures 2, 3, and 7(b); the Table III 50-km system-level
case; analytical/event-driven M2 cross-validation; the HFT operational
waterfall; and finite-grid hardware-resource optimization.

The Figure 5 gate recomputes the independent Q1+AB bounds. It reuses the
previously validated 577.8-second explicit-strategy fields after checking
configuration compatibility. This limitation is recorded in the final JSON
and does not change the corresponding paper-level `PARTIAL` status.

## Interpretation

A Phase 15 PASS means the implemented, version-pinned scope is internally
consistent, reproducible under the recorded environment, and protected by the
listed independent oracles. It does not imply that every published plot or
microscopic hardware model has been reproduced.

The reproduction matrix intentionally retains:

- `PARTIAL` for plots without author pointwise data and for the Table III
  displayed values whose rounding intervals disagree with the equations;
- `INSUFFICIENT_INFORMATION` for the microscopic TPI, measurement, and CAPS
  models requiring unavailable pulse data or author code;
- `NOT_IMPLEMENTED` for the optional generic Bell-operator optimizer.

These statuses are scientific boundaries, not failed Phase 15 regressions.

## Reproduction Command

```bash
python3 experiments/final_validation/run_phase15.py
python3 -m pytest tests/scientific/test_phase15_final_validation_artifacts.py -q
```

The runner writes regenerated experiment outputs only to temporary
directories. It fails if tracked result artifacts are modified during the
audit.
