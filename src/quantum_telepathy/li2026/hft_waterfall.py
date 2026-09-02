"""Ding-to-Li operational-advantage waterfall for two-party HFT-style games."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import Enum

from quantum_telepathy.core.xor_game import Matrix2x2
from quantum_telepathy.ding_jiang.hft import ideal_hedging_values
from quantum_telepathy.li2026.fidelity import (
    fidelity_threshold,
    noisy_gap,
    noisy_quantum_value,
)
from quantum_telepathy.li2026.lctc import (
    check_latency_constraint,
    generalized_lctc_utility,
    generalized_lctc_values,
)
from quantum_telepathy.li2026.operational import CriterionStatus, DecisionCriterion
from quantum_telepathy.li2026.statistics import (
    certification_p_value,
    expected_score_threshold,
    expected_win_count,
    required_score_trials,
    required_trial_rate,
    required_trials,
    score_certification_p_value,
)


class StatisticsMethod(str, Enum):
    """Finite-statistics interpretation used by the HFT workflow."""

    EXACT_BINOMIAL = "exact_binomial"
    GENERAL_SCORE_BOUND = "general_score_bound"


def _finite_nonnegative(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be a finite nonnegative value")
    return result


def _strict_probability(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or not 0.0 < result < 1.0:
        raise ValueError(f"{name} must be a finite value in (0, 1)")
    return result


def _infer_statistics_method(beta1: float, beta2: float) -> StatisticsMethod:
    utility_values = {
        value
        for input_row in generalized_lctc_utility(beta1, beta2)
        for parity_pair in input_row
        for value in parity_pair
    }
    if utility_values <= {0.0, 1.0}:
        return StatisticsMethod.EXACT_BINOMIAL
    return StatisticsMethod.GENERAL_SCORE_BOUND


def _status(condition: bool) -> CriterionStatus:
    return CriterionStatus.from_condition(condition)


@dataclass(frozen=True)
class HFTWaterfallResult:
    """Traceable theoretical-to-operational HFT feasibility decomposition."""

    scenario_id: str
    ding_p: float
    ding_beta: float
    ding_classical_value: float
    ding_quantum_value: float
    ding_ideal_gap: float
    input_distribution: Matrix2x2
    beta1: float
    beta2: float
    li_classical_value: float
    li_quantum_value: float
    li_ideal_gap: float
    model_transition_gap_change: float
    epsilon: float
    epsilon_threshold: float | None
    noisy_quantum_value: float
    noisy_gap: float
    physical_gap_retained_fraction: float | None
    statistics_method: StatisticsMethod
    score_min: float
    score_max: float
    alpha: float
    n_req: int | None
    expected_score_threshold_at_n_req: int | None
    p_value_or_bound_at_n_req: float | None
    t_env: float
    r_req: float | None
    r_heg: float
    rate_margin_hz: float | None
    tau_rot: float
    tau_meas: float
    tau_dec: float
    t_loc: float
    t_comm: float
    decision_margin_seconds: float
    communication_margin_seconds: float
    latency_constrained_regime: CriterionStatus
    theoretical_advantage: CriterionStatus
    fidelity_criterion: CriterionStatus
    statistical_certification: CriterionStatus
    rate_criterion: CriterionStatus
    decision_criterion: CriterionStatus
    overall_operational_quantum_advantage: CriterionStatus
    first_failed_criterion: str | None
    dominant_bottleneck: str
    normalized_criterion_margins: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready result with explicit PASS/FAIL strings."""

        output = asdict(self)
        for key, value in tuple(output.items()):
            if isinstance(value, Enum):
                output[key] = value.value
        return output

    def stages(self) -> tuple[dict[str, object], ...]:
        """Return the ordered waterfall stages without implying additive losses."""

        ding_status = _status(self.ding_ideal_gap > 0.0)
        return (
            {
                "order": 1,
                "stage": "ding_jiang_ideal",
                "gap": self.ding_ideal_gap,
                "status": ding_status.value,
            },
            {
                "order": 2,
                "stage": "li_generalized_ideal",
                "gap": self.li_ideal_gap,
                "gap_change_from_ding": self.model_transition_gap_change,
                "status": self.theoretical_advantage.value,
            },
            {
                "order": 3,
                "stage": "physical_infidelity",
                "gap": self.noisy_gap,
                "retained_fraction": self.physical_gap_retained_fraction,
                "status": self.fidelity_criterion.value,
            },
            {
                "order": 4,
                "stage": "finite_statistics",
                "n_req": self.n_req,
                "p_value_or_bound": self.p_value_or_bound_at_n_req,
                "statistics_method": self.statistics_method.value,
                "status": self.statistical_certification.value,
            },
            {
                "order": 5,
                "stage": "heg_rate",
                "r_req": self.r_req,
                "r_heg": self.r_heg,
                "status": self.rate_criterion.value,
            },
            {
                "order": 6,
                "stage": "local_decision_latency",
                "tau_dec": self.tau_dec,
                "t_loc": self.t_loc,
                "status": self.decision_criterion.value,
            },
            {
                "order": 7,
                "stage": "overall_operational_feasibility",
                "t_comm": self.t_comm,
                "status": self.overall_operational_quantum_advantage.value,
                "dominant_bottleneck": self.dominant_bottleneck,
            },
        )


def _failure_and_bottleneck(
    statuses: tuple[tuple[str, bool], ...],
    margins: dict[str, float],
) -> tuple[str | None, str]:
    for name, passes in statuses:
        if not passes:
            return name, name
    return None, min(margins, key=margins.__getitem__)


def evaluate_hft_waterfall(
    *,
    scenario_id: str,
    ding_p: float,
    ding_beta: float,
    input_distribution: Matrix2x2,
    beta1: float,
    beta2: float,
    epsilon: float,
    alpha: float,
    t_env: float,
    r_heg: float,
    tau_rot: float,
    tau_meas: float,
    t_loc: float,
    t_comm: float,
    statistics_method: StatisticsMethod | str | None = None,
    max_rounds: int = 100_000_000,
    chunk_size: int = 32_768,
) -> HFTWaterfallResult:
    """Evaluate the complete Ding-ideal to Li-operational HFT waterfall."""

    if not scenario_id:
        raise ValueError("scenario_id must be nonempty")
    combined_error = _finite_nonnegative("epsilon", epsilon)
    if combined_error > 1.0:
        raise ValueError("epsilon must be in [0, 1]")
    significance = _strict_probability("alpha", alpha)
    stationary_window = _finite_nonnegative("t_env", t_env)
    if stationary_window == 0.0:
        raise ValueError("t_env must be positive")
    entanglement_rate = _finite_nonnegative("r_heg", r_heg)
    communication_time = _finite_nonnegative("t_comm", t_comm)
    decision = DecisionCriterion(tau_rot=tau_rot, tau_meas=tau_meas, t_loc=t_loc)

    ding = ideal_hedging_values(ding_p, ding_beta)
    li = generalized_lctc_values(input_distribution, beta1, beta2)
    threshold = (
        fidelity_threshold(li.classical_bias, li.quantum_bias)
        if li.quantum_bias > 0.0
        else None
    )
    noisy_value = noisy_quantum_value(combined_error, li.quantum_bias)
    physical_gap = noisy_gap(combined_error, li.classical_bias, li.quantum_bias)
    theoretical = li.gap > 0.0
    fidelity_passes = (
        theoretical and threshold is not None and combined_error < threshold
    )

    utility = generalized_lctc_utility(beta1, beta2)
    utility_values = tuple(
        value
        for input_row in utility
        for parity_pair in input_row
        for value in parity_pair
    )
    score_min = min(utility_values)
    score_max = max(utility_values)
    method = (
        _infer_statistics_method(beta1, beta2)
        if statistics_method is None
        else StatisticsMethod(statistics_method)
    )
    n_req: int | None = None
    expected_threshold: int | None = None
    p_value: float | None = None
    r_req: float | None = None
    statistical_passes = False
    rate_passes = False
    if fidelity_passes:
        if method is StatisticsMethod.EXACT_BINOMIAL:
            n_req = required_trials(
                li.classical_value,
                noisy_value,
                significance,
                max_rounds=max_rounds,
                chunk_size=chunk_size,
            )
            expected_threshold = expected_win_count(n_req, noisy_value)
            p_value = certification_p_value(
                n_req, li.classical_value, noisy_value
            )
        else:
            n_req = required_score_trials(
                li.classical_value,
                noisy_value,
                significance,
                score_min,
                score_max,
                max_rounds=max_rounds,
                chunk_size=chunk_size,
            )
            expected_threshold = expected_score_threshold(n_req, noisy_value)
            p_value = score_certification_p_value(
                n_req,
                li.classical_value,
                noisy_value,
                score_min,
                score_max,
            )
        statistical_passes = p_value < significance
        r_req = required_trial_rate(n_req, stationary_window)
        rate_passes = statistical_passes and entanglement_rate > r_req

    latency_passes = check_latency_constraint(decision.t_loc, communication_time)
    decision_passes = decision.status is CriterionStatus.PASS
    overall = all(
        (
            latency_passes,
            theoretical,
            fidelity_passes,
            statistical_passes,
            rate_passes,
            decision_passes,
        )
    )

    margins: dict[str, float] = {}
    if threshold is not None and threshold > 0.0:
        margins["fidelity_criterion"] = (threshold - combined_error) / threshold
    if r_req is not None and r_req > 0.0:
        margins["rate_criterion"] = (entanglement_rate - r_req) / r_req
    if decision.t_loc > 0.0:
        margins["decision_criterion"] = (
            decision.t_loc - decision.tau_dec
        ) / decision.t_loc
    if communication_time > 0.0:
        margins["latency_constrained_regime"] = (
            communication_time - decision.t_loc
        ) / communication_time

    ordered_statuses = (
        ("theoretical_advantage", theoretical),
        ("fidelity_criterion", fidelity_passes),
        ("statistical_certification", statistical_passes),
        ("rate_criterion", rate_passes),
        ("decision_criterion", decision_passes),
        ("latency_constrained_regime", latency_passes),
    )
    first_failure, bottleneck = _failure_and_bottleneck(ordered_statuses, margins)
    retained_fraction = physical_gap / li.gap if li.gap > 0.0 else None

    return HFTWaterfallResult(
        scenario_id=scenario_id,
        ding_p=ding_p,
        ding_beta=ding_beta,
        ding_classical_value=ding.classical_value,
        ding_quantum_value=ding.quantum_value,
        ding_ideal_gap=ding.gap,
        input_distribution=input_distribution,
        beta1=beta1,
        beta2=beta2,
        li_classical_value=li.classical_value,
        li_quantum_value=li.quantum_value,
        li_ideal_gap=li.gap,
        model_transition_gap_change=li.gap - ding.gap,
        epsilon=combined_error,
        epsilon_threshold=threshold,
        noisy_quantum_value=noisy_value,
        noisy_gap=physical_gap,
        physical_gap_retained_fraction=retained_fraction,
        statistics_method=method,
        score_min=score_min,
        score_max=score_max,
        alpha=significance,
        n_req=n_req,
        expected_score_threshold_at_n_req=expected_threshold,
        p_value_or_bound_at_n_req=p_value,
        t_env=stationary_window,
        r_req=r_req,
        r_heg=entanglement_rate,
        rate_margin_hz=(entanglement_rate - r_req) if r_req is not None else None,
        tau_rot=decision.tau_rot,
        tau_meas=decision.tau_meas,
        tau_dec=decision.tau_dec,
        t_loc=decision.t_loc,
        t_comm=communication_time,
        decision_margin_seconds=decision.t_loc - decision.tau_dec,
        communication_margin_seconds=communication_time - decision.t_loc,
        latency_constrained_regime=_status(latency_passes),
        theoretical_advantage=_status(theoretical),
        fidelity_criterion=_status(fidelity_passes),
        statistical_certification=_status(statistical_passes),
        rate_criterion=_status(rate_passes),
        decision_criterion=decision.status,
        overall_operational_quantum_advantage=_status(overall),
        first_failed_criterion=first_failure,
        dominant_bottleneck=bottleneck,
        normalized_criterion_margins=margins,
    )
