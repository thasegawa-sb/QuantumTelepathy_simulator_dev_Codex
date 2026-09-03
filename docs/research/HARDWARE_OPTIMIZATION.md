# Hardware-Resource Optimization

## Scope

Phase 13 is a new research extension built on the validated Ding-Jiang v3 HFT
model and Li et al. v1 operational criteria and system-level TPI equations. It
does not reproduce a figure or table from either paper. It asks which configured
hardware changes make all operational criteria pass simultaneously.

The multiparty CAPS architecture is excluded because its microscopic rate and
fidelity model is distinct from the bipartite Table III TPI architecture.

## Search Definition

Each scenario-distance case exhaustively evaluates 4,864 candidates. The nine
cases therefore contain 43,776 evaluated designs. The variables are:

| Lever | Configured values |
|---|---|
| State-infidelity scale | `1, 0.5, 0.25, 0.1` |
| Measurement-infidelity scale | `1, 0.5` |
| Detector headroom fraction | `0, 1` |
| Optical headroom fraction | `0, 1` |
| Decision-time scale | `1, 0.5` |
| Memory-lifetime multiplier | `1, 2` |
| Memory qubits | `250, 419` |
| Parallel channels | integers `1` through `16`, then `24, 32, 48` |

Distance-dependent transmission and latency use the physical laws
`10^(-alpha L/10)` and `L/v_g`. The rounded 50 km Table III overrides remain
part of the paper reproduction but are deliberately removed from this sweep.

Every candidate must satisfy the theoretical, fidelity, finite-statistics,
HEG-rate, local-decision, strict LCTC, memory-domain, memory-lifetime, and
network-domain checks. Memory depth need not saturate the intrinsic attempt rate;
finite depth is already accounted for by `min(1/tau_e, N_a/tau_occ)`.

## Optimization Semantics

The result is exact on the configured finite lattice. No continuous global
optimality is claimed. A candidate is Pareto optimal when no feasible candidate
uses no more normalized improvement in every lever and strictly less in at
least one. The normalized effort scale is not a financial or engineering cost
estimate. Equal weights provide a deterministic representative only; the full
Pareto front is the cost-agnostic output.

Search outcomes distinguish:

| Status | Meaning |
|---|---|
| `BASELINE_FEASIBLE` | No hardware improvement is required |
| `FEASIBLE` | At least one improved design passes |
| `INFEASIBLE_SEARCH_SPACE` | Every valid candidate was evaluated and none passes |
| `EVALUATION_FAILED` | No candidate could be evaluated |

## Results

For the Ding representative `p=0.3`, `beta=0.3`, `T_env=1 s` case:

| Distance | Status | Selected state-error scale | Memory | Channels | `n_req` | `R_HEG` |
|---:|---|---:|---:|---:|---:|---:|
| 25 km | FEASIBLE | 1 | 250 | 2 | 65,629 | 103,856/s |
| 50 km | FEASIBLE | 1 | 250 | 9 | 66,133 | 66,778/s |
| 75 km | FEASIBLE | 0.5 | 250 | 5 | 5,306 | 5,886/s |
| 100 km | FEASIBLE | 0.25 | 250 | 14 | 2,861 | 2,936/s |
| 125 km | FEASIBLE | 0.25 | 419 | 48 | 2,871 | 3,204/s |
| 150 km | INFEASIBLE_SEARCH_SPACE | 0.1 best tested | 419 | 48 | 1,857 | 1,223/s best tested |

Thus 125 km is the maximum feasible configured distance, not a continuous
distance threshold. At 50 km, the unchanged-fidelity single-lever calculation
requires exactly 9 channels: 8 fail the strict rate inequality and 9 pass.

With `T_loc=0.5 us`, the 50 km representative case additionally requires the
configured 0.5 decision-time scale, giving `tau_dec=0.485 us`, together with 9
channels in the equal-weight recommendation.

The correlated asymmetric fidelity-stress case is substantially harder. Only 2
of 4,864 candidates pass. The selected candidate uses state-error scale `0.1`,
measurement-error scale `0.5`, unit detector and optics efficiency, 2x memory
lifetime, 419 memories, and 48 channels. It gives effective
`epsilon=0.00934847`, `n_req=1,132,017`, and `R_HEG=1,140,196/s`. This exposes
the amplification from a small theoretical utility gap to a severe operational
statistics and throughput requirement.

The flat-utility control has no theoretical gap and is reported as
`INFEASIBLE_SEARCH_SPACE`, with zero evaluation errors. It is not mislabeled as
an optimizer convergence failure.

## Validation

- All 43,776 configured candidates evaluate without error.
- An independently written dominance scan finds no dominated front member and
  no feasible candidate left uncovered by the reported Pareto fronts.
- Analytical strict channel transitions agree with enumerated candidates.
- Every selected recommendation exactly matches a direct Phase 11 operational
  reevaluation for `epsilon`, `n_req`, `R_req`, rate, latency, and all standard
  PASS/FAIL statuses.
- The attenuation and propagation laws agree to the configured `1e-12`
  absolute tolerance.

## Artifacts

- Configuration: `experiments/li2026/configs/hardware_optimization_v1.json`
- Oracle: `experiments/li2026/oracles/hardware_optimization_v1.json`
- All candidates: `experiments/li2026/results/hardware_optimization_v1/hardware_candidates.csv`
- Pareto fronts: `experiments/li2026/results/hardware_optimization_v1/pareto_front.csv`
- Recommendations: `experiments/li2026/results/hardware_optimization_v1/recommended_designs.csv`
- Figure: `experiments/li2026/results/hardware_optimization_v1/hardware_optimization.png`
- Summary: `experiments/li2026/results/hardware_optimization_v1/hardware_optimization_summary.json`
