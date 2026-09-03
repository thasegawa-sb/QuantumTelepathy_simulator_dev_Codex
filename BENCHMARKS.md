# Performance Benchmarks

Last benchmark run: 2026-09-03.

Phase 14 optimizes only workflows that already have independent scientific
oracles. Runtime improvements do not relax numerical tolerances, discrete
minimality, strict operational inequalities, or paper-reproduction status.

## Reproduction

Run the isolated-process benchmark suite:

```bash
python3 experiments/performance/benchmark_phase14.py
```

Configuration and committed output:

- `experiments/performance/configs/phase14_v1.json`
- `experiments/performance/results/phase14_v1/phase14_benchmark_summary.json`

Each target runs in a fresh subprocess. The recorded peak RSS is the operating
system process high-water mark and includes imported numerical libraries. Wall
time is compared with the historical baseline only when Python major/minor,
operating system, and machine architecture match.

## Environment

| Item | Value |
|---|---|
| Platform | macOS 15.5, arm64 |
| Python | 3.13.5 |
| Baseline commit | `95bb7e224d39b998d31c088903d06a314acc6ce1` |
| Baseline date | 2026-09-03 |
| Candidate workload | 9 cases, 43,776 finite-grid candidates per repetition |

Exact dependency versions are emitted by the benchmark summary rather than
duplicated here.

## Results

| Target | Repetitions | Median runtime | Peak RSS | Scientific gate |
|---|---:|---:|---:|---|
| Hardware grid, baseline | 3 | 13.204 s | 261.6 MB | Signature `a495...8620` |
| Hardware grid, optimized | 3 | 5.696 s | 251.4 MB | Same signature; PASS |
| Finite-statistics fixtures | 5 | 0.0351 s | 108.3 MB | `n_req=238, 66133`; PASS |
| Figure 5 representative Q1+AB threshold | 3 | 0.2286 s | 107.2 MB | Bracket `[0.931640625, 0.931966146]`; PASS |

The optimized hardware-grid median is 43.1% of baseline, a 56.9% reduction.
Peak RSS is 96.1% of baseline; the small memory difference is reported but is
not treated as a portable performance claim.

The cProfile end-to-end run, including artifact and plot generation, changed as
follows:

| Profile quantity | Baseline | Optimized | Change |
|---|---:|---:|---:|
| Total profiled time | 28.404 s | 15.111 s | -46.8% |
| Hardware-search cumulative time | 19.784 s | 9.001 s | -54.5% |
| General-score search cumulative time | 10.397 s | 5.629 s | -45.9% |
| Function calls | 121,352,596 | 49,737,456 | -59.0% |
| Generalized-game evaluations | 43,783 | 16 expected outside profiling noise | Removed from candidate loop |

The generalized-game count after optimization is one per search case in the
core workflow; the profile also includes seven direct operational
reevaluations, so the expected end-to-end count is 16.

## Implemented Optimizations

1. Compute generalized LCTC game values, fidelity threshold, and utility score
   range once per scenario-distance search instead of once per candidate.
2. Return the flat eight-component cost vector directly instead of recursively
   converting its dataclass for every Pareto comparison.
3. Grow exact finite-statistics search blocks from 256 entries up to the
   configured maximum while preserving an exhaustive contiguous scan.
4. Skip the second binomial log-survival evaluation when the general-score
   interpolation fraction is zero. This is the common `[0,1]` score case.

Chunk-size invariance is checked against independent exhaustive oracles. The
full hardware result is protected by an exact digest over case statuses,
counts, recommendations, required rates, HEG rates, infidelities, and costs.

## SDP Decision

The representative Ding-Jiang Figure 5 Q1+AB threshold workflow is already
solver-dominated and completes in about 0.23 seconds with 12 threshold
evaluations and stable `optimal` statuses. Process parallelism was not added:
the full cross-section workflow is dominated by the separate explicit-strategy
lower-bound search, and concurrent conic solves would add oversubscription and
determinism risks without changing the deferred full-surface evidence gap.

The full 101x101 Figure 5 surface remains `PARTIAL`; this benchmark does not
turn unavailable author data or unpublished modified-NPA details into a PASS.
