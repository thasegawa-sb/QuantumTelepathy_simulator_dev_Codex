# Roadmap

Current validation gate: Phase 15, final validation.

## Completed

| Date | Item | Evidence |
|---|---|---|
| 2026-08-31 | Phase 0 literature/design audit | `docs/research/*MODEL_MAP.md`, `docs/research/REPRODUCTION_MATRIX.md` |
| 2026-09-01 | Initialized fresh Git repository | `.git` created after user instruction |
| 2026-09-01 | Implemented minimal Layer 0/1 scientific core | `src/quantum_telepathy/core/` |
| 2026-09-01 | Added Ding-Jiang v3 and Li v1 utility/fidelity fixtures | `src/quantum_telepathy/ding_jiang/`, `src/quantum_telepathy/li2026/` |
| 2026-09-01 | Passed initial analytical tests | `python3 -m pytest`, 23 passed |
| 2026-09-01 | Recomputed Ding-Jiang v3 Figure 3 on a 101x101 grid | `experiments/ding_jiang/results/fig3_v3/` |
| 2026-09-01 | Passed Figure 3 analytical and independent-classical gates | `python3 -m pytest`, 278 passed |
| 2026-09-01 | Reproduced the Ding-Jiang Section 4.1 lossy representative case | `experiments/ding_jiang/results/loss_example_v3/` |
| 2026-09-01 | Cross-validated Eq. A.11/A.12 and threshold search | `python3 -m pytest`, 285 passed |
| 2026-09-01 | Reproduced the Ding-Jiang v3 Type II memory calculation | `experiments/ding_jiang/results/type_ii_memory_v3/` |
| 2026-09-01 | Cross-validated Type II formulas with independent Decimal and closed-form oracles | `python3 -m pytest`, 300 passed |
| 2026-09-01 | Implemented Ding-Jiang Eq. 4.2-4.3 qubit depolarizing noise and robustness | `src/quantum_telepathy/ding_jiang/noise.py` |
| 2026-09-01 | Generated Figure 7-8 data and plots with analytical validation | `experiments/ding_jiang/results/noise_robustness_v3/` |
| 2026-09-02 | Reproduced Ding-Jiang Figure 5(b,c) on documented 0.1 cross-sections | `experiments/ding_jiang/results/fig5_cross_sections_v3/` |
| 2026-09-02 | Added independent real NPA `Q1+AB` lossy-value bounds and two-sided numerical threshold brackets | `src/quantum_telepathy/ding_jiang/loss_sdp.py` |
| 2026-09-02 | Implemented Li correlated inputs, asymmetric utilities, Werner-state and measurement-error reference paths | `src/quantum_telepathy/li2026/` |
| 2026-09-02 | Generated Li v1 Figure 2(a-c) data and plot; all configured analytical and independent-code gates pass | `experiments/li2026/results/fig2_v1/` |
| 2026-09-02 | Implemented stable exact-binomial finite-statistics certification and independent Decimal oracles | `src/quantum_telepathy/li2026/statistics.py` |
| 2026-09-02 | Generated Li v1 Figure 3 rate curves; all configured equation and discrete-minimality gates pass | `experiments/li2026/results/fig3_v1/` |
| 2026-09-02 | Implemented Li Eq. 44-45 decision latency and the Table II operational-status schema | `src/quantum_telepathy/li2026/operational.py` |
| 2026-09-02 | Implemented Li Eq. 46-53 analytical M2 occupancy, memory fidelity, and HEG throughput | `src/quantum_telepathy/hardware/` |
| 2026-09-02 | Completed the Li Table III 50 km system-level calculation and documented four paper-value discrepancies | `experiments/li2026/results/table3_50km_v1/` |
| 2026-09-03 | Cross-validated analytical M2 throughput and occupancy with a 256-seed discrete-event simulation | `experiments/li2026/results/m2_event_cross_validation_v1/` |
| 2026-09-03 | Completed the configuration-driven Ding-to-Li HFT operational-advantage waterfall | `experiments/li2026/results/hft_waterfall_v1/` |
| 2026-09-03 | Implemented and independently validated the Li Eq. 20 general-score finite-statistics bound | `src/quantum_telepathy/li2026/statistics.py` |
| 2026-09-03 | Implemented the Li three-party XOR/GHZ game, 64-strategy classical oracle, and Appendix B noise model | `src/quantum_telepathy/multiparty/`, `src/quantum_telepathy/li2026/multiparty.py` |
| 2026-09-03 | Reproduced the Li Figure 7(b) computation on a 101x101 grid with independent phase optimization | `experiments/li2026/results/fig7b_v1/` |
| 2026-09-03 | Completed exhaustive finite-grid hardware-resource optimization and Pareto analysis | `experiments/li2026/results/hardware_optimization_v1/` |
| 2026-09-03 | Completed deterministic performance optimization and isolated runtime/memory benchmarks | `BENCHMARKS.md`, `experiments/performance/results/phase14_v1/` |

## Next Gates

1. Complete Phase 15 final validation:
   - run the complete test suite,
   - rerun all practical paper reproductions and cross-validations,
   - verify committed artifacts, discrepancy statuses, and parameter provenance,
   - retain the documented full Figure 5 and microscopic-model limitations.

## Phase 16 Deliverables

Phase 16 will produce exactly three final narrative artifacts:

1. Japanese simulator manual in Word format (`.docx`).
2. Japanese research report in Word format (`.docx`).
3. English research paper in LaTeX format (`.tex` plus required bibliography/assets).

Development traceability Markdown files and generated numerical/figure artifacts remain
supporting project records, not additional Phase 16 narrative deliverables.

## Deferred

| Topic | Reason |
|---|---|
| Ding-Jiang full Figure 5(a) 101x101 surface | Cross-sections and independent bounds pass; a fresh 22-point run took 578 s, author pointwise data and unpublished modified-NPA code are unavailable |
| Microscopic cQED/TPI/CAPS models | System-level model is mandatory first; appendix-level microscopic reproduction may need further data |
