"""Operational quantum-advantage criteria from Li et al. Eqs. 38-45.

All durations use seconds and all rates use inverse seconds.  The statistical
status is a prospective certification calculation at the expected quantum win
count from Li Eq. 40; it is not a substitute for a p-value from observed data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from enum import Enum
from numbers import Integral

from quantum_telepathy.li2026.fidelity import (
    combined_infidelity,
    fidelity_threshold,
    noisy_gap,
    noisy_quantum_value,
)
from quantum_telepathy.li2026.lctc import check_latency_constraint
from quantum_telepathy.li2026.statistics import (
    certification_p_value,
    expected_win_count,
    required_trial_rate,
    required_trials,
)


class CriterionStatus(str, Enum):
    """Machine-readable status used by the standardized operational output."""

    PASS = "PASS"
    FAIL = "FAIL"

    @classmethod
    def from_condition(cls, condition: bool) -> CriterionStatus:
        return cls.PASS if condition else cls.FAIL


def _finite_nonnegative(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be a finite nonnegative value")
    return result


def _bias(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be a finite value in [0, 1]")
    return result


def _probability(name: str, value: float, *, strict: bool = False) -> float:
    result = float(value)
    lower_ok = result > 0.0 if strict else result >= 0.0
    upper_ok = result < 1.0 if strict else result <= 1.0
    if not math.isfinite(result) or not lower_ok or not upper_ok:
        interval = "(0, 1)" if strict else "[0, 1]"
        raise ValueError(f"{name} must be a finite value in {interval}")
    return result


def _positive_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


@dataclass(frozen=True)
class DecisionCriterion:
    """Li Eqs. 44-45 with strict completion inside the local window."""

    tau_rot: float
    tau_meas: float
    t_loc: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "tau_rot", _finite_nonnegative("tau_rot", self.tau_rot))
        object.__setattr__(
            self,
            "tau_meas",
            _finite_nonnegative("tau_meas", self.tau_meas),
        )
        object.__setattr__(self, "t_loc", _finite_nonnegative("t_loc", self.t_loc))
        if not math.isfinite(self.tau_rot + self.tau_meas):
            raise ValueError("tau_dec must be finite")

    @property
    def tau_dec(self) -> float:
        """Return Eq. 44, ``tau_dec = tau_rot + tau_meas``."""

        return self.tau_rot + self.tau_meas

    @property
    def status(self) -> CriterionStatus:
        """Return PASS exactly when Eq. 45, ``tau_dec < T_loc``, holds."""

        return CriterionStatus.from_condition(self.tau_dec < self.t_loc)


@dataclass(frozen=True)
class OperationalAdvantageStatus:
    """Traceable Table II status and the quantities used to obtain it."""

    latency_constrained_regime: CriterionStatus
    theoretical_advantage: CriterionStatus
    fidelity_criterion: CriterionStatus
    statistical_certification: CriterionStatus
    rate_criterion: CriterionStatus
    decision_criterion: CriterionStatus
    overall_operational_quantum_advantage: CriterionStatus
    classical_bias: float
    quantum_bias: float
    classical_value: float
    ideal_quantum_value: float
    noisy_quantum_value: float
    ideal_gap: float
    noisy_gap: float
    epsilon_s: float | None
    epsilon_meas: float | None
    epsilon: float
    epsilon_threshold: float | None
    alpha: float
    n_req: int | None
    expected_wins_at_n_req: int | None
    p_value_at_n_req: float | None
    t_env: float
    r_req: float | None
    r_heg: float
    tau_rot: float
    tau_meas: float
    tau_dec: float
    t_loc: float
    t_comm: float

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready dictionary with explicit PASS/FAIL strings."""

        output: dict[str, object] = {}
        for field in fields(self):
            value = getattr(self, field.name)
            output[field.name] = value.value if isinstance(value, CriterionStatus) else value
        return output


def _evaluate_operational_advantage(
    *,
    classical_bias: float,
    quantum_bias: float,
    epsilon: float,
    alpha: float,
    t_env: float,
    r_heg: float,
    tau_rot: float,
    tau_meas: float,
    t_loc: float,
    t_comm: float,
    epsilon_s: float | None,
    epsilon_meas: float | None,
    max_rounds: int,
    chunk_size: int,
) -> OperationalAdvantageStatus:
    c_bias = _bias("classical_bias", classical_bias)
    q_bias = _bias("quantum_bias", quantum_bias)
    combined_error = _probability("epsilon", epsilon)
    significance = _probability("alpha", alpha, strict=True)
    environment_window = _finite_nonnegative("t_env", t_env)
    if environment_window == 0.0:
        raise ValueError("t_env must be positive")
    entanglement_rate = _finite_nonnegative("r_heg", r_heg)
    communication_time = _finite_nonnegative("t_comm", t_comm)
    search_limit = _positive_integer("max_rounds", max_rounds)
    search_chunk = _positive_integer("chunk_size", chunk_size)
    decision = DecisionCriterion(tau_rot=tau_rot, tau_meas=tau_meas, t_loc=t_loc)

    classical_value = (1.0 + c_bias) / 2.0
    ideal_quantum_value = (1.0 + q_bias) / 2.0
    noisy_value = noisy_quantum_value(combined_error, q_bias)
    ideal_gap = (q_bias - c_bias) / 2.0
    physical_gap = noisy_gap(combined_error, c_bias, q_bias)

    theoretical = q_bias > c_bias
    threshold = fidelity_threshold(c_bias, q_bias) if q_bias > 0.0 else None
    fidelity = theoretical and threshold is not None and combined_error < threshold

    n_req: int | None = None
    expected_wins: int | None = None
    p_value: float | None = None
    r_req: float | None = None
    statistically_certifiable = False
    rate_passes = False
    if fidelity:
        n_req = required_trials(
            classical_value,
            noisy_value,
            significance,
            max_rounds=search_limit,
            chunk_size=search_chunk,
        )
        expected_wins = expected_win_count(n_req, noisy_value)
        p_value = certification_p_value(n_req, classical_value, noisy_value)
        statistically_certifiable = p_value < significance
        r_req = required_trial_rate(n_req, environment_window)
        rate_passes = statistically_certifiable and entanglement_rate > r_req

    latency_regime = check_latency_constraint(decision.t_loc, communication_time)
    decision_passes = decision.status is CriterionStatus.PASS
    overall = all(
        (
            latency_regime,
            theoretical,
            fidelity,
            statistically_certifiable,
            rate_passes,
            decision_passes,
        )
    )

    return OperationalAdvantageStatus(
        latency_constrained_regime=CriterionStatus.from_condition(latency_regime),
        theoretical_advantage=CriterionStatus.from_condition(theoretical),
        fidelity_criterion=CriterionStatus.from_condition(fidelity),
        statistical_certification=CriterionStatus.from_condition(
            statistically_certifiable
        ),
        rate_criterion=CriterionStatus.from_condition(rate_passes),
        decision_criterion=decision.status,
        overall_operational_quantum_advantage=CriterionStatus.from_condition(overall),
        classical_bias=c_bias,
        quantum_bias=q_bias,
        classical_value=classical_value,
        ideal_quantum_value=ideal_quantum_value,
        noisy_quantum_value=noisy_value,
        ideal_gap=ideal_gap,
        noisy_gap=physical_gap,
        epsilon_s=epsilon_s,
        epsilon_meas=epsilon_meas,
        epsilon=combined_error,
        epsilon_threshold=threshold,
        alpha=significance,
        n_req=n_req,
        expected_wins_at_n_req=expected_wins,
        p_value_at_n_req=p_value,
        t_env=environment_window,
        r_req=r_req,
        r_heg=entanglement_rate,
        tau_rot=decision.tau_rot,
        tau_meas=decision.tau_meas,
        tau_dec=decision.tau_dec,
        t_loc=decision.t_loc,
        t_comm=communication_time,
    )


def evaluate_operational_advantage(
    *,
    classical_bias: float,
    quantum_bias: float,
    epsilon: float,
    alpha: float,
    t_env: float,
    r_heg: float,
    tau_rot: float,
    tau_meas: float,
    t_loc: float,
    t_comm: float,
    max_rounds: int = 100_000_000,
    chunk_size: int = 32_768,
) -> OperationalAdvantageStatus:
    """Evaluate all currently required bipartite operational criteria.

    ``epsilon`` is the already-combined Li Eq. 30 infidelity.  Use
    :func:`evaluate_operational_advantage_from_error_components` when the state
    and measurement errors are available separately.
    """

    return _evaluate_operational_advantage(
        classical_bias=classical_bias,
        quantum_bias=quantum_bias,
        epsilon=epsilon,
        alpha=alpha,
        t_env=t_env,
        r_heg=r_heg,
        tau_rot=tau_rot,
        tau_meas=tau_meas,
        t_loc=t_loc,
        t_comm=t_comm,
        epsilon_s=None,
        epsilon_meas=None,
        max_rounds=max_rounds,
        chunk_size=chunk_size,
    )


def evaluate_operational_advantage_from_error_components(
    *,
    classical_bias: float,
    quantum_bias: float,
    epsilon_s: float,
    epsilon_meas: float,
    alpha: float,
    t_env: float,
    r_heg: float,
    tau_rot: float,
    tau_meas: float,
    t_loc: float,
    t_comm: float,
    max_rounds: int = 100_000_000,
    chunk_size: int = 32_768,
) -> OperationalAdvantageStatus:
    """Evaluate the status after combining Eq. 26 and Eq. 28 errors exactly."""

    state_error = _probability("epsilon_s", epsilon_s)
    measurement_error = _probability("epsilon_meas", epsilon_meas)
    return _evaluate_operational_advantage(
        classical_bias=classical_bias,
        quantum_bias=quantum_bias,
        epsilon=combined_infidelity(state_error, measurement_error),
        alpha=alpha,
        t_env=t_env,
        r_heg=r_heg,
        tau_rot=tau_rot,
        tau_meas=tau_meas,
        t_loc=t_loc,
        t_comm=t_comm,
        epsilon_s=state_error,
        epsilon_meas=measurement_error,
        max_rounds=max_rounds,
        chunk_size=chunk_size,
    )
