# Roadmap

Current validation gate: Phase 3 partial, foundational nonlocal/XOR core.

## Completed

| Date | Item | Evidence |
|---|---|---|
| 2026-08-31 | Phase 0 literature/design audit | `docs/research/*MODEL_MAP.md`, `docs/research/REPRODUCTION_MATRIX.md` |
| 2026-09-01 | Initialized fresh Git repository | `.git` created after user instruction |
| 2026-09-01 | Implemented minimal Layer 0/1 scientific core | `src/quantum_telepathy/core/` |
| 2026-09-01 | Added Ding-Jiang v3 and Li v1 utility/fidelity fixtures | `src/quantum_telepathy/ding_jiang/`, `src/quantum_telepathy/li2026/` |
| 2026-09-01 | Passed initial analytical tests | `python3 -m pytest`, 23 passed |

## Next Gates

1. Implement Li finite-statistics certification:
   - exact binomial-tail p-value,
   - `n_req(epsilon,M,alpha)`,
   - `R_req(epsilon,M,alpha,T_env)`,
   - small-n brute-force or direct-sum oracle.

2. Add Ding-Jiang reproduction scripts:
   - biased CHSH sweep,
   - Ding Eq. 3.1/Fig. 3 grid,
   - result metadata with paper version.

3. Add Li Fig. 2 reproduction scripts:
   - independent Bernoulli inputs,
   - correlated inputs,
   - asymmetric beta cases,
   - fidelity-threshold plots/data.

4. Implement Li operational status object:
   - theoretical advantage,
   - fidelity criterion,
   - statistical certification,
   - rate criterion,
   - decision criterion,
   - overall operational quantum advantage.

5. Implement M2 analytical HEG/time-multiplexing model:
   - occupancy,
   - memory depth,
   - attempt rate,
   - HEG throughput,
   - Table III 50 km benchmark.

## Deferred

| Topic | Reason |
|---|---|
| Event-driven network simulation | Analytical Li formulas must pass first |
| Microscopic cQED/TPI/CAPS models | System-level model is mandatory first; appendix-level microscopic reproduction may need further data |
| Multiparty LCTC | Defer until two-party gates are validated |
| Hardware optimization | Defer until all operational criteria and Table III are validated |
