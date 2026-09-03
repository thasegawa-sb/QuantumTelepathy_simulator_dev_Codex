"""Finite-lattice hardware optimization for operational LCTC advantage.

The cost model is an explicit, dimensionless search-space normalization. It is
not a monetary or experimental-development cost model. The Pareto set is the
primary output; a weighted recommendation is reported only for a pinned set of
weights.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from enum import Enum
from itertools import product
from numbers import Integral
from typing import Any, Iterable, Sequence

from quantum_telepathy.core.xor_game import Matrix2x2
from quantum_telepathy.hardware.memory_m0_m1_m2 import (
    evaluate_m2_memory_fidelity,
)
from quantum_telepathy.hardware.yb_node import (
    YbSystemLevelParameters,
    evaluate_yb_system_level,
)
from quantum_telepathy.li2026.fidelity import (
    fidelity_threshold,
    noisy_quantum_value,
)
from quantum_telepathy.li2026.hft_waterfall import (
    HFTWaterfallResult,
    StatisticsMethod,
    evaluate_hft_waterfall,
)
from quantum_telepathy.li2026.lctc import (
    check_latency_constraint,
    generalized_lctc_utility,
    generalized_lctc_values,
)
from quantum_telepathy.li2026.operational import CriterionStatus
from quantum_telepathy.li2026.statistics import (
    CertificationSearchLimitError,
    NoFiniteCertificationError,
    certification_p_value,
    expected_score_threshold,
    expected_win_count,
    required_score_trials,
    required_trial_rate,
    required_trials,
    score_certification_p_value,
)


def _finite(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _finite_positive(name: str, value: float) -> float:
    result = _finite(name, value)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _unit_interval(name: str, value: float) -> float:
    result = _finite(name, value)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return result


def _reduction_scale(name: str, value: float) -> float:
    result = _finite(name, value)
    if not 0.0 < result <= 1.0:
        raise ValueError(f"{name} must be in (0, 1]")
    return result


def _positive_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _strict_probability(name: str, value: float) -> float:
    result = _finite(name, value)
    if not 0.0 < result < 1.0:
        raise ValueError(f"{name} must be in (0, 1)")
    return result


def _status(condition: bool) -> CriterionStatus:
    return CriterionStatus.from_condition(condition)


def _json_ready(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


class HardwareSearchStatus(str, Enum):
    """Outcome classes that separate infeasibility from evaluation failure."""

    BASELINE_FEASIBLE = "BASELINE_FEASIBLE"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE_SEARCH_SPACE = "INFEASIBLE_SEARCH_SPACE"
    EVALUATION_FAILED = "EVALUATION_FAILED"


@dataclass(frozen=True)
class HardwareOptimizationScenario:
    """Pinned game and application inputs for one optimization problem."""

    scenario_id: str
    ding_p: float
    ding_beta: float
    input_distribution: Matrix2x2
    beta1: float
    beta2: float
    statistics_method: StatisticsMethod | str
    alpha: float
    t_env: float
    t_loc: float
    max_rounds: int = 100_000_000
    chunk_size: int = 32_768

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id must be nonempty")
        object.__setattr__(
            self, "statistics_method", StatisticsMethod(self.statistics_method)
        )
        object.__setattr__(self, "alpha", _strict_probability("alpha", self.alpha))
        object.__setattr__(self, "t_env", _finite_positive("t_env", self.t_env))
        object.__setattr__(self, "t_loc", _finite_positive("t_loc", self.t_loc))
        object.__setattr__(
            self, "max_rounds", _positive_integer("max_rounds", self.max_rounds)
        )
        object.__setattr__(
            self, "chunk_size", _positive_integer("chunk_size", self.chunk_size)
        )


@dataclass(frozen=True, order=True)
class HardwareImprovementDesign:
    """Improvement levers relative to one system-level baseline."""

    state_infidelity_scale: float = 1.0
    measurement_infidelity_scale: float = 1.0
    detector_headroom_fraction: float = 0.0
    optics_headroom_fraction: float = 0.0
    decision_time_scale: float = 1.0
    memory_lifetime_multiplier: float = 1.0
    n_memory_qubits: int = 1
    n_channels: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "state_infidelity_scale",
            _reduction_scale(
                "state_infidelity_scale", self.state_infidelity_scale
            ),
        )
        object.__setattr__(
            self,
            "measurement_infidelity_scale",
            _reduction_scale(
                "measurement_infidelity_scale",
                self.measurement_infidelity_scale,
            ),
        )
        object.__setattr__(
            self,
            "detector_headroom_fraction",
            _unit_interval(
                "detector_headroom_fraction", self.detector_headroom_fraction
            ),
        )
        object.__setattr__(
            self,
            "optics_headroom_fraction",
            _unit_interval(
                "optics_headroom_fraction", self.optics_headroom_fraction
            ),
        )
        object.__setattr__(
            self,
            "decision_time_scale",
            _reduction_scale("decision_time_scale", self.decision_time_scale),
        )
        lifetime = _finite_positive(
            "memory_lifetime_multiplier", self.memory_lifetime_multiplier
        )
        if lifetime < 1.0:
            raise ValueError("memory_lifetime_multiplier must be at least 1")
        object.__setattr__(self, "memory_lifetime_multiplier", lifetime)
        object.__setattr__(
            self,
            "n_memory_qubits",
            _positive_integer("n_memory_qubits", self.n_memory_qubits),
        )
        object.__setattr__(
            self, "n_channels", _positive_integer("n_channels", self.n_channels)
        )


def _unique_sorted(
    name: str,
    values: Iterable[Any],
    converter: Any,
) -> tuple[Any, ...]:
    converted = tuple(converter(name, value) for value in values)
    if not converted:
        raise ValueError(f"{name} must be nonempty")
    return tuple(sorted(set(converted)))


@dataclass(frozen=True)
class HardwareSearchSpace:
    """Finite design lattice and explicit scalar-cost weights."""

    state_infidelity_scales: tuple[float, ...]
    measurement_infidelity_scales: tuple[float, ...]
    detector_headroom_fractions: tuple[float, ...]
    optics_headroom_fractions: tuple[float, ...]
    decision_time_scales: tuple[float, ...]
    memory_lifetime_multipliers: tuple[float, ...]
    n_memory_qubits: tuple[int, ...]
    n_channels: tuple[int, ...]
    cost_weights: tuple[float, float, float, float, float, float, float, float] = (
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "state_infidelity_scales",
            _unique_sorted(
                "state_infidelity_scales",
                self.state_infidelity_scales,
                _reduction_scale,
            ),
        )
        object.__setattr__(
            self,
            "measurement_infidelity_scales",
            _unique_sorted(
                "measurement_infidelity_scales",
                self.measurement_infidelity_scales,
                _reduction_scale,
            ),
        )
        object.__setattr__(
            self,
            "detector_headroom_fractions",
            _unique_sorted(
                "detector_headroom_fractions",
                self.detector_headroom_fractions,
                _unit_interval,
            ),
        )
        object.__setattr__(
            self,
            "optics_headroom_fractions",
            _unique_sorted(
                "optics_headroom_fractions",
                self.optics_headroom_fractions,
                _unit_interval,
            ),
        )
        object.__setattr__(
            self,
            "decision_time_scales",
            _unique_sorted(
                "decision_time_scales",
                self.decision_time_scales,
                _reduction_scale,
            ),
        )
        object.__setattr__(
            self,
            "memory_lifetime_multipliers",
            _unique_sorted(
                "memory_lifetime_multipliers",
                self.memory_lifetime_multipliers,
                _finite_positive,
            ),
        )
        if self.memory_lifetime_multipliers[0] < 1.0:
            raise ValueError("memory lifetime multipliers must be at least 1")
        object.__setattr__(
            self,
            "n_memory_qubits",
            _unique_sorted(
                "n_memory_qubits", self.n_memory_qubits, _positive_integer
            ),
        )
        object.__setattr__(
            self,
            "n_channels",
            _unique_sorted("n_channels", self.n_channels, _positive_integer),
        )
        if len(self.cost_weights) != 8:
            raise ValueError("cost_weights must contain eight entries")
        weights = tuple(_finite("cost_weight", value) for value in self.cost_weights)
        if any(value < 0.0 for value in weights) or sum(weights) <= 0.0:
            raise ValueError("cost weights must be nonnegative with a positive sum")
        object.__setattr__(self, "cost_weights", weights)

    @property
    def candidate_count(self) -> int:
        dimensions = (
            self.state_infidelity_scales,
            self.measurement_infidelity_scales,
            self.detector_headroom_fractions,
            self.optics_headroom_fractions,
            self.decision_time_scales,
            self.memory_lifetime_multipliers,
            self.n_memory_qubits,
            self.n_channels,
        )
        return math.prod(len(values) for values in dimensions)

    def designs(self) -> Iterable[HardwareImprovementDesign]:
        """Yield every configured design in deterministic lexicographic order."""

        return (
            HardwareImprovementDesign(*values)
            for values in product(
                self.state_infidelity_scales,
                self.measurement_infidelity_scales,
                self.detector_headroom_fractions,
                self.optics_headroom_fractions,
                self.decision_time_scales,
                self.memory_lifetime_multipliers,
                self.n_memory_qubits,
                self.n_channels,
            )
        )


@dataclass(frozen=True)
class HardwareCostVector:
    """Normalized improvement effort in each independently reported lever."""

    state_fidelity: float
    measurement_fidelity: float
    detector_efficiency: float
    optics_efficiency: float
    decision_speed: float
    memory_lifetime: float
    memory_count: float
    channel_count: float

    def values(self) -> tuple[float, ...]:
        return tuple(asdict(self).values())


def _normalized_reduction(value: float, minimum: float) -> float:
    if minimum == 1.0:
        return 0.0
    return math.log(1.0 / value) / math.log(1.0 / minimum)


def _normalized_increase(value: float, baseline: float, maximum: float) -> float:
    if maximum == baseline:
        return 0.0
    return (value - baseline) / (maximum - baseline)


def _cost_vector(
    design: HardwareImprovementDesign,
    search_space: HardwareSearchSpace,
    baseline: YbSystemLevelParameters,
) -> HardwareCostVector:
    return HardwareCostVector(
        state_fidelity=_normalized_reduction(
            design.state_infidelity_scale,
            min(search_space.state_infidelity_scales),
        ),
        measurement_fidelity=_normalized_reduction(
            design.measurement_infidelity_scale,
            min(search_space.measurement_infidelity_scales),
        ),
        detector_efficiency=(
            design.detector_headroom_fraction
            / max(search_space.detector_headroom_fractions)
            if max(search_space.detector_headroom_fractions) > 0.0
            else 0.0
        ),
        optics_efficiency=(
            design.optics_headroom_fraction
            / max(search_space.optics_headroom_fractions)
            if max(search_space.optics_headroom_fractions) > 0.0
            else 0.0
        ),
        decision_speed=_normalized_reduction(
            design.decision_time_scale,
            min(search_space.decision_time_scales),
        ),
        memory_lifetime=(
            math.log(design.memory_lifetime_multiplier)
            / math.log(max(search_space.memory_lifetime_multipliers))
            if max(search_space.memory_lifetime_multipliers) > 1.0
            else 0.0
        ),
        memory_count=_normalized_increase(
            design.n_memory_qubits,
            baseline.n_memory_qubits,
            max(search_space.n_memory_qubits),
        ),
        channel_count=_normalized_increase(
            design.n_channels,
            baseline.n_channels,
            max(search_space.n_channels),
        ),
    )


def apply_hardware_improvements(
    baseline: YbSystemLevelParameters,
    design: HardwareImprovementDesign,
    distance_km: float,
) -> YbSystemLevelParameters:
    """Apply a design and force physical distance laws instead of table overrides."""

    distance = _finite("distance_km", distance_km)
    if distance < 0.0:
        raise ValueError("distance_km must be nonnegative")
    if design.n_memory_qubits < baseline.n_memory_qubits:
        raise ValueError("n_memory_qubits cannot be below the baseline")
    if design.n_channels < baseline.n_channels:
        raise ValueError("n_channels cannot be below the baseline")

    detector = baseline.detector_efficiency + design.detector_headroom_fraction * (
        1.0 - baseline.detector_efficiency
    )
    optics = baseline.optics_efficiency + design.optics_headroom_fraction * (
        1.0 - baseline.optics_efficiency
    )
    return replace(
        baseline,
        state_infidelity_upper_bound=(
            baseline.state_infidelity_upper_bound * design.state_infidelity_scale
        ),
        measurement_infidelity=(
            baseline.measurement_infidelity
            * design.measurement_infidelity_scale
        ),
        detector_efficiency=detector,
        optics_efficiency=optics,
        rotation_time=baseline.rotation_time * design.decision_time_scale,
        measurement_time=baseline.measurement_time * design.decision_time_scale,
        memory_lifetime=(
            baseline.memory_lifetime * design.memory_lifetime_multiplier
        ),
        n_memory_qubits=design.n_memory_qubits,
        n_channels=design.n_channels,
        distance_km=distance,
        link_transmission_override=None,
        link_latency_override=None,
    )


@dataclass(frozen=True)
class _CertificationResult:
    n_req: int | None
    expected_threshold: int | None
    p_value: float | None
    r_req: float | None
    passes: bool
    search_limit_exceeded: bool


@dataclass(frozen=True)
class HardwareCandidateEvaluation:
    """A fully derived design point and every operational constraint."""

    scenario_id: str
    distance_km: float
    design: HardwareImprovementDesign
    cost_vector: HardwareCostVector
    weighted_cost: float
    changed_lever_count: int
    state_infidelity: float
    measurement_infidelity: float
    detector_efficiency: float
    optics_efficiency: float
    tau_rot: float
    tau_meas: float
    tau_dec: float
    tau_link: float
    tau_occ: float
    memory_lifetime: float
    minimum_memory_qubits: int
    memory_depth_sufficient: bool
    entanglement_success_probability: float
    gamma_heg: float
    r_heg: float
    epsilon: float | None
    epsilon_threshold: float | None
    tau_mem_threshold: float | None
    n_req: int | None
    expected_score_threshold_at_n_req: int | None
    p_value_or_bound_at_n_req: float | None
    r_req: float | None
    latency_constrained_regime: CriterionStatus
    theoretical_advantage: CriterionStatus
    memory_model_domain: CriterionStatus
    memory_lifetime_criterion: CriterionStatus
    fidelity_criterion: CriterionStatus
    statistical_certification: CriterionStatus
    rate_criterion: CriterionStatus
    decision_criterion: CriterionStatus
    network_model_domain: CriterionStatus
    overall_operational_quantum_advantage: CriterionStatus
    certification_search_limit_exceeded: bool
    constraint_violations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return _json_ready(asdict(self))


@dataclass(frozen=True)
class HardwareSearchResult:
    """Exhaustive-search result with a finite-grid Pareto certificate."""

    scenario_id: str
    distance_km: float
    search_status: HardwareSearchStatus
    search_method: str
    candidate_count: int
    evaluated_count: int
    evaluation_error_count: int
    certification_limit_count: int
    feasible_count: int
    pareto_count: int
    baseline: HardwareCandidateEvaluation | None
    recommended: HardwareCandidateEvaluation | None
    pareto_front: tuple[HardwareCandidateEvaluation, ...]
    candidates: tuple[HardwareCandidateEvaluation, ...]
    evaluation_errors: tuple[str, ...]

    def to_dict(self, *, include_candidates: bool = False) -> dict[str, Any]:
        output = {
            "scenario_id": self.scenario_id,
            "distance_km": self.distance_km,
            "search_status": self.search_status.value,
            "search_method": self.search_method,
            "candidate_count": self.candidate_count,
            "evaluated_count": self.evaluated_count,
            "evaluation_error_count": self.evaluation_error_count,
            "certification_limit_count": self.certification_limit_count,
            "feasible_count": self.feasible_count,
            "pareto_count": self.pareto_count,
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "recommended": (
                self.recommended.to_dict() if self.recommended else None
            ),
            "pareto_front": [candidate.to_dict() for candidate in self.pareto_front],
            "evaluation_errors": list(self.evaluation_errors),
        }
        if include_candidates:
            output["candidates"] = [candidate.to_dict() for candidate in self.candidates]
        return output


def classify_search_status(
    *,
    evaluated_count: int,
    feasible_count: int,
    baseline_feasible: bool,
) -> HardwareSearchStatus:
    """Classify an exhaustive search without conflating absence and failure."""

    if evaluated_count < 0 or feasible_count < 0 or feasible_count > evaluated_count:
        raise ValueError("search counts are inconsistent")
    if baseline_feasible:
        return HardwareSearchStatus.BASELINE_FEASIBLE
    if evaluated_count == 0:
        return HardwareSearchStatus.EVALUATION_FAILED
    if feasible_count > 0:
        return HardwareSearchStatus.FEASIBLE
    return HardwareSearchStatus.INFEASIBLE_SEARCH_SPACE


def nondominated_indices(
    cost_vectors: Sequence[Sequence[float]],
    *,
    tolerance: float = 1e-12,
) -> tuple[int, ...]:
    """Return exact finite-set Pareto indices for minimization objectives."""

    tol = _finite("tolerance", tolerance)
    if tol < 0.0:
        raise ValueError("tolerance must be nonnegative")
    if not cost_vectors:
        return ()
    arity = len(cost_vectors[0])
    if arity == 0 or any(len(vector) != arity for vector in cost_vectors):
        raise ValueError("cost vectors must have one common positive arity")
    vectors = tuple(tuple(_finite("cost", value) for value in row) for row in cost_vectors)

    def dominates(left: Sequence[float], right: Sequence[float]) -> bool:
        return all(a <= b + tol for a, b in zip(left, right, strict=True)) and any(
            a < b - tol for a, b in zip(left, right, strict=True)
        )

    front: list[int] = []
    for index, vector in enumerate(vectors):
        if any(dominates(vectors[other], vector) for other in front):
            continue
        front = [
            other for other in front if not dominates(vector, vectors[other])
        ]
        front.append(index)
    return tuple(front)


def _changed_lever_count(
    design: HardwareImprovementDesign,
    baseline: YbSystemLevelParameters,
) -> int:
    return sum(
        (
            design.state_infidelity_scale != 1.0,
            design.measurement_infidelity_scale != 1.0,
            design.detector_headroom_fraction != 0.0,
            design.optics_headroom_fraction != 0.0,
            design.decision_time_scale != 1.0,
            design.memory_lifetime_multiplier != 1.0,
            design.n_memory_qubits != baseline.n_memory_qubits,
            design.n_channels != baseline.n_channels,
        )
    )


def _baseline_design(
    baseline: YbSystemLevelParameters,
) -> HardwareImprovementDesign:
    return HardwareImprovementDesign(
        n_memory_qubits=baseline.n_memory_qubits,
        n_channels=baseline.n_channels,
    )


def _certification_result(
    scenario: HardwareOptimizationScenario,
    classical_value: float,
    noisy_value: float,
    score_min: float,
    score_max: float,
) -> _CertificationResult:
    try:
        if scenario.statistics_method is StatisticsMethod.EXACT_BINOMIAL:
            n_req = required_trials(
                classical_value,
                noisy_value,
                scenario.alpha,
                max_rounds=scenario.max_rounds,
                chunk_size=scenario.chunk_size,
            )
            expected = expected_win_count(n_req, noisy_value)
            p_value = certification_p_value(n_req, classical_value, noisy_value)
        else:
            n_req = required_score_trials(
                classical_value,
                noisy_value,
                scenario.alpha,
                score_min,
                score_max,
                max_rounds=scenario.max_rounds,
                chunk_size=scenario.chunk_size,
            )
            expected = expected_score_threshold(n_req, noisy_value)
            p_value = score_certification_p_value(
                n_req,
                classical_value,
                noisy_value,
                score_min,
                score_max,
            )
    except (CertificationSearchLimitError, NoFiniteCertificationError):
        return _CertificationResult(None, None, None, None, False, True)
    return _CertificationResult(
        n_req=n_req,
        expected_threshold=expected,
        p_value=p_value,
        r_req=required_trial_rate(n_req, scenario.t_env),
        passes=p_value < scenario.alpha,
        search_limit_exceeded=False,
    )


def _evaluate_candidate(
    *,
    baseline: YbSystemLevelParameters,
    scenario: HardwareOptimizationScenario,
    distance_km: float,
    design: HardwareImprovementDesign,
    search_space: HardwareSearchSpace,
    certification_cache: dict[str, _CertificationResult],
) -> HardwareCandidateEvaluation:
    parameters = apply_hardware_improvements(baseline, design, distance_km)
    system = evaluate_yb_system_level(parameters)
    game = generalized_lctc_values(
        scenario.input_distribution, scenario.beta1, scenario.beta2
    )
    theoretical = game.gap > 0.0
    threshold = (
        fidelity_threshold(game.classical_bias, game.quantum_bias)
        if game.quantum_bias > 0.0
        else None
    )
    epsilon = system.memory_adjusted_combined_infidelity_upper_bound
    memory = (
        evaluate_m2_memory_fidelity(
            tau_occ=system.timing.tau_occ,
            tau_mem=parameters.memory_lifetime,
            epsilon_s=parameters.state_infidelity_upper_bound,
            epsilon_meas=parameters.measurement_infidelity,
            epsilon_threshold=threshold,
        )
        if threshold is not None and 0.0 <= threshold <= 1.0
        else None
    )
    memory_domain = memory is not None and memory.model_domain_valid
    memory_lifetime = memory is not None and memory.memory_lifetime_criterion
    fidelity = (
        theoretical
        and epsilon is not None
        and threshold is not None
        and memory is not None
        and memory.fidelity_criterion
        and epsilon < threshold
    )

    utility = generalized_lctc_utility(scenario.beta1, scenario.beta2)
    utility_values = tuple(
        value
        for input_row in utility
        for parity_pair in input_row
        for value in parity_pair
    )
    certification = _CertificationResult(None, None, None, None, False, False)
    if fidelity and epsilon is not None:
        cache_key = epsilon.hex()
        cached_certification = certification_cache.get(cache_key)
        if cached_certification is None:
            certification = _certification_result(
                scenario,
                game.classical_value,
                noisy_quantum_value(epsilon, game.quantum_bias),
                min(utility_values),
                max(utility_values),
            )
            certification_cache[cache_key] = certification
        else:
            certification = cached_certification

    rate = (
        certification.passes
        and certification.r_req is not None
        and system.rate.r_heg > certification.r_req
    )
    decision = system.tau_dec < scenario.t_loc
    latency_regime = check_latency_constraint(scenario.t_loc, system.tau_link)
    network_domain = system.false_positive_model_domain_valid
    overall = all(
        (
            latency_regime,
            theoretical,
            memory_domain,
            memory_lifetime,
            fidelity,
            certification.passes,
            rate,
            decision,
            network_domain,
        )
    )
    criteria = (
        ("latency_constrained_regime", latency_regime),
        ("theoretical_advantage", theoretical),
        ("memory_model_domain", memory_domain),
        ("memory_lifetime_criterion", memory_lifetime),
        ("fidelity_criterion", fidelity),
        ("statistical_certification", certification.passes),
        ("rate_criterion", rate),
        ("decision_criterion", decision),
        ("network_model_domain", network_domain),
    )
    costs = _cost_vector(design, search_space, baseline)
    weighted_cost = sum(
        weight * cost
        for weight, cost in zip(
            search_space.cost_weights, costs.values(), strict=True
        )
    )
    return HardwareCandidateEvaluation(
        scenario_id=scenario.scenario_id,
        distance_km=float(distance_km),
        design=design,
        cost_vector=costs,
        weighted_cost=weighted_cost,
        changed_lever_count=_changed_lever_count(design, baseline),
        state_infidelity=parameters.state_infidelity_upper_bound,
        measurement_infidelity=parameters.measurement_infidelity,
        detector_efficiency=parameters.detector_efficiency,
        optics_efficiency=parameters.optics_efficiency,
        tau_rot=parameters.rotation_time,
        tau_meas=parameters.measurement_time,
        tau_dec=system.tau_dec,
        tau_link=system.tau_link,
        tau_occ=system.timing.tau_occ,
        memory_lifetime=parameters.memory_lifetime,
        minimum_memory_qubits=system.timing.minimum_memory_qubits,
        memory_depth_sufficient=system.timing.memory_depth_sufficient,
        entanglement_success_probability=system.entanglement_success_probability,
        gamma_heg=system.timing.gamma_heg,
        r_heg=system.rate.r_heg,
        epsilon=epsilon,
        epsilon_threshold=threshold,
        tau_mem_threshold=(
            memory.tau_mem_threshold
            if memory is not None and math.isfinite(memory.tau_mem_threshold)
            else None
        ),
        n_req=certification.n_req,
        expected_score_threshold_at_n_req=certification.expected_threshold,
        p_value_or_bound_at_n_req=certification.p_value,
        r_req=certification.r_req,
        latency_constrained_regime=_status(latency_regime),
        theoretical_advantage=_status(theoretical),
        memory_model_domain=_status(memory_domain),
        memory_lifetime_criterion=_status(memory_lifetime),
        fidelity_criterion=_status(fidelity),
        statistical_certification=_status(certification.passes),
        rate_criterion=_status(rate),
        decision_criterion=_status(decision),
        network_model_domain=_status(network_domain),
        overall_operational_quantum_advantage=_status(overall),
        certification_search_limit_exceeded=(
            certification.search_limit_exceeded
        ),
        constraint_violations=tuple(name for name, passes in criteria if not passes),
    )


def search_hardware_designs(
    *,
    baseline: YbSystemLevelParameters,
    scenario: HardwareOptimizationScenario,
    distance_km: float,
    search_space: HardwareSearchSpace,
) -> HardwareSearchResult:
    """Exhaustively search one configured distance and return its Pareto set."""

    distance = _finite("distance_km", distance_km)
    if distance < 0.0:
        raise ValueError("distance_km must be nonnegative")
    if min(search_space.n_memory_qubits) < baseline.n_memory_qubits:
        raise ValueError("search memory counts cannot be below the baseline")
    if min(search_space.n_channels) < baseline.n_channels:
        raise ValueError("search channel counts cannot be below the baseline")

    baseline_design = _baseline_design(baseline)
    baseline_coordinates = (
        baseline_design.state_infidelity_scale in search_space.state_infidelity_scales,
        baseline_design.measurement_infidelity_scale
        in search_space.measurement_infidelity_scales,
        baseline_design.detector_headroom_fraction
        in search_space.detector_headroom_fractions,
        baseline_design.optics_headroom_fraction
        in search_space.optics_headroom_fractions,
        baseline_design.decision_time_scale in search_space.decision_time_scales,
        baseline_design.memory_lifetime_multiplier
        in search_space.memory_lifetime_multipliers,
        baseline_design.n_memory_qubits in search_space.n_memory_qubits,
        baseline_design.n_channels in search_space.n_channels,
    )
    if not all(baseline_coordinates):
        raise ValueError("search space must contain the unchanged baseline design")

    certification_cache: dict[str, _CertificationResult] = {}
    evaluations: list[HardwareCandidateEvaluation] = []
    errors: list[str] = []
    for design in search_space.designs():
        try:
            evaluations.append(
                _evaluate_candidate(
                    baseline=baseline,
                    scenario=scenario,
                    distance_km=distance,
                    design=design,
                    search_space=search_space,
                    certification_cache=certification_cache,
                )
            )
        except (ArithmeticError, RuntimeError, ValueError) as error:
            errors.append(f"{design}: {type(error).__name__}: {error}")

    baseline_evaluation = next(
        (item for item in evaluations if item.design == baseline_design), None
    )
    if baseline_evaluation is None:
        try:
            baseline_evaluation = _evaluate_candidate(
                baseline=baseline,
                scenario=scenario,
                distance_km=distance,
                design=baseline_design,
                search_space=search_space,
                certification_cache=certification_cache,
            )
        except (ArithmeticError, RuntimeError, ValueError) as error:
            errors.append(
                f"baseline: {type(error).__name__}: {error}"
            )

    feasible = [
        item
        for item in evaluations
        if item.overall_operational_quantum_advantage is CriterionStatus.PASS
    ]
    pareto_indices = nondominated_indices(
        [item.cost_vector.values() for item in feasible]
    )
    pareto = tuple(feasible[index] for index in pareto_indices)
    recommended = min(
        feasible,
        key=lambda item: (
            item.weighted_cost,
            item.changed_lever_count,
            item.cost_vector.values(),
            item.design,
        ),
        default=None,
    )
    baseline_feasible = (
        baseline_evaluation is not None
        and baseline_evaluation.overall_operational_quantum_advantage
        is CriterionStatus.PASS
    )
    return HardwareSearchResult(
        scenario_id=scenario.scenario_id,
        distance_km=distance,
        search_status=classify_search_status(
            evaluated_count=len(evaluations),
            feasible_count=len(feasible),
            baseline_feasible=baseline_feasible,
        ),
        search_method="exhaustive_finite_grid",
        candidate_count=search_space.candidate_count,
        evaluated_count=len(evaluations),
        evaluation_error_count=len(errors),
        certification_limit_count=sum(
            item.certification_search_limit_exceeded for item in evaluations
        ),
        feasible_count=len(feasible),
        pareto_count=len(pareto),
        baseline=baseline_evaluation,
        recommended=recommended,
        pareto_front=pareto,
        candidates=tuple(evaluations),
        evaluation_errors=tuple(errors[:20]),
    )


def direct_operational_reevaluation(
    candidate: HardwareCandidateEvaluation,
    scenario: HardwareOptimizationScenario,
) -> HFTWaterfallResult:
    """Reevaluate a selected candidate through the validated Phase 11 API."""

    if candidate.epsilon is None:
        raise ValueError("candidate has no physical combined infidelity")
    return evaluate_hft_waterfall(
        scenario_id=scenario.scenario_id,
        ding_p=scenario.ding_p,
        ding_beta=scenario.ding_beta,
        input_distribution=scenario.input_distribution,
        beta1=scenario.beta1,
        beta2=scenario.beta2,
        epsilon=candidate.epsilon,
        alpha=scenario.alpha,
        t_env=scenario.t_env,
        r_heg=candidate.r_heg,
        tau_rot=candidate.tau_rot,
        tau_meas=candidate.tau_meas,
        t_loc=scenario.t_loc,
        t_comm=candidate.tau_link,
        statistics_method=scenario.statistics_method,
        max_rounds=scenario.max_rounds,
        chunk_size=scenario.chunk_size,
    )
