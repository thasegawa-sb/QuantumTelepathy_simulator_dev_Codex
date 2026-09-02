"""Li et al. three-party majority XOR/GHZ model from Eqs. 62-67 and App. B."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import Enum
from itertools import product

import numpy as np
from numpy.typing import NDArray

from quantum_telepathy.core.classical import (
    ClassicalOptimizationResult,
    maximize_classical_value,
)
from quantum_telepathy.li2026.lctc import check_latency_constraint
from quantum_telepathy.li2026.operational import CriterionStatus, DecisionCriterion
from quantum_telepathy.li2026.statistics import (
    certification_p_value,
    expected_win_count,
    required_trial_rate,
    required_trials,
)
from quantum_telepathy.multiparty.xor import (
    GHZOptimizationResult,
    InputTuple,
    deterministic_classical_bias,
    ghz_bias_at_phases,
    independent_bernoulli_distribution,
    symmetric_ghz_equatorial_bias,
    xor_coefficients,
)


def _probability(name: str, value: float, *, strict: bool = False) -> float:
    result = float(value)
    lower = result > 0.0 if strict else result >= 0.0
    upper = result < 1.0 if strict else result <= 1.0
    if not math.isfinite(result) or not lower or not upper:
        interval = "(0, 1)" if strict else "[0, 1]"
        raise ValueError(f"{name} must be a finite value in {interval}")
    return result


def _finite_nonnegative(name: str, value: float) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be a finite nonnegative value")
    return result


def majority(inputs: InputTuple) -> int:
    """Return Li Eqs. 63/B6 for a three-bit input tuple."""

    if len(inputs) != 3 or any(value not in (0, 1) for value in inputs):
        raise ValueError("inputs must contain exactly three binary values")
    return int(sum(inputs) > 1.5)


def three_party_majority_utility(beta: float):
    """Return the parity utility in Li Eqs. 62 and 65/B12."""

    softness = _probability("beta", beta)

    def utility(parity: int, inputs: InputTuple) -> float:
        if parity not in (0, 1):
            raise ValueError("parity must be binary")
        target = majority(inputs)
        hard_utility = float(parity == target)
        if sum(inputs) % 3 == 0:
            return hard_utility
        return (1.0 - softness) * hard_utility + softness * (1.0 - hard_utility)

    return utility


def three_party_input_distribution(probability_one: float) -> dict[InputTuple, float]:
    """Return the IID Bernoulli family used in Li Figure 7(b)."""

    return independent_bernoulli_distribution(3, probability_one)


def three_party_game_coefficients(
    probability_one: float,
    beta: float,
) -> dict[InputTuple, float]:
    """Return the coefficients ``M_x`` in Li Eqs. 67/B14."""

    return xor_coefficients(
        three_party_input_distribution(probability_one),
        three_party_majority_utility(beta),
    )


@dataclass(frozen=True)
class ThreePartyValueResult:
    """Classical and GHZ-equatorial values for the Figure 7(b) game."""

    classical_bias: float
    quantum_bias: float
    classical_value: float
    quantum_value: float
    gap: float
    phase_offset: float
    phase_steps: tuple[float, float, float]
    optimization_method: str


def three_party_values(probability_one: float, beta: float) -> ThreePartyValueResult:
    """Evaluate Li Eqs. B13-B15 for the symmetric IID three-party game."""

    coefficients = three_party_game_coefficients(probability_one, beta)
    classical = deterministic_classical_bias(coefficients)
    quantum: GHZOptimizationResult = symmetric_ghz_equatorial_bias(coefficients)
    classical_value = (1.0 + classical.bias) / 2.0
    quantum_value = (1.0 + quantum.bias) / 2.0
    return ThreePartyValueResult(
        classical_bias=classical.bias,
        quantum_bias=quantum.bias,
        classical_value=classical_value,
        quantum_value=quantum_value,
        gap=quantum_value - classical_value,
        phase_offset=quantum.phase_offset,
        phase_steps=quantum.phase_steps,  # type: ignore[arg-type]
        optimization_method=quantum.method,
    )


def enumerated_three_party_classical_optimum(
    probability_one: float,
    beta: float,
) -> ClassicalOptimizationResult:
    """Independently maximize utility over all 64 local output maps."""

    distribution = three_party_input_distribution(probability_one)
    parity_utility = three_party_majority_utility(beta)

    def utility(inputs: InputTuple, outputs: tuple[int, ...]) -> float:
        return parity_utility(sum(outputs) % 2, inputs)

    return maximize_classical_value(
        observation_sets=((0, 1),) * 3,
        decision_sets=((0, 1),) * 3,
        input_distribution=distribution,
        utility=utility,
    )


def canonical_paper_strategy_bias() -> float:
    """Evaluate the Eq. B10 strategy ``phi0=-pi/4, phi_i=pi/2``."""

    coefficients = three_party_game_coefficients(0.5, 0.0)
    return ghz_bias_at_phases(
        coefficients,
        phase_offset=-math.pi / 4.0,
        phase_steps=(math.pi / 2.0,) * 3,
    )


def ghz_state_vector() -> NDArray[np.complex128]:
    """Return ``(|000>+|111>)/sqrt(2)``."""

    state = np.zeros(8, dtype=np.complex128)
    state[0] = 1.0 / math.sqrt(2.0)
    state[7] = 1.0 / math.sqrt(2.0)
    return state


def noisy_ghz_state(epsilon_ghz: float) -> NDArray[np.complex128]:
    """Return the three-qubit GHZ infidelity model in Li Eq. B16."""

    state_error = _probability("epsilon_ghz", epsilon_ghz)
    ghz = ghz_state_vector()
    projector = np.outer(ghz, ghz.conjugate())
    return (1.0 - state_error) * projector + (state_error / 7.0) * (
        np.eye(8, dtype=np.complex128) - projector
    )


def combined_ghz_infidelity(epsilon_ghz: float, epsilon_meas: float) -> float:
    """Return the exact effective correlator infidelity in Li Eq. B18."""

    state_error = _probability("epsilon_ghz", epsilon_ghz)
    measurement_error = _probability("epsilon_meas", epsilon_meas)
    return 1.0 - (1.0 - 8.0 * state_error / 7.0) * (
        1.0 - 2.0 * measurement_error
    ) ** 3


def noisy_ghz_correlator(
    epsilon_ghz: float,
    epsilon_meas: float,
    measurement_angles: tuple[float, float, float],
) -> float:
    """Evaluate Li Eqs. B16-B18 directly by an 8x8 density-matrix trace."""

    measurement_error = _probability("epsilon_meas", epsilon_meas)
    if len(measurement_angles) != 3 or any(
        not math.isfinite(float(angle)) for angle in measurement_angles
    ):
        raise ValueError("measurement_angles must contain three finite values")
    pauli_x = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
    pauli_y = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)
    visibility = 1.0 - 2.0 * measurement_error
    observables = tuple(
        visibility
        * (math.cos(angle) * pauli_x + math.sin(angle) * pauli_y)
        for angle in measurement_angles
    )
    joint = np.kron(np.kron(observables[0], observables[1]), observables[2])
    correlator = np.trace(noisy_ghz_state(epsilon_ghz) @ joint)
    if abs(float(correlator.imag)) > 1e-12:
        raise ArithmeticError("GHZ correlator has an unexpected imaginary component")
    return float(correlator.real)


def noisy_three_party_quantum_value(
    combined_infidelity: float,
    ideal_quantum_value: float,
) -> float:
    """Return the noisy value in Li Eq. B19."""

    epsilon = _finite_nonnegative("combined_infidelity", combined_infidelity)
    quantum = float(ideal_quantum_value)
    if not math.isfinite(quantum) or not 0.0 <= quantum <= 1.0:
        raise ValueError("ideal_quantum_value must be a finite value in [0, 1]")
    return quantum - epsilon * (quantum - 0.5)


def three_party_fidelity_threshold(
    classical_value: float,
    ideal_quantum_value: float,
) -> float:
    """Return the effective infidelity threshold in Li Eq. B21."""

    classical = float(classical_value)
    quantum = float(ideal_quantum_value)
    if not all(math.isfinite(value) for value in (classical, quantum)):
        raise ValueError("game values must be finite")
    if quantum <= 0.5:
        raise ValueError("ideal_quantum_value must exceed 1/2")
    return (quantum - classical) / (quantum - 0.5)


@dataclass(frozen=True)
class MultipartyOperationalStatus:
    """Prospective three-party operational-advantage status."""

    latency_constrained_regime: CriterionStatus
    theoretical_advantage: CriterionStatus
    fidelity_criterion: CriterionStatus
    statistical_certification: CriterionStatus
    rate_criterion: CriterionStatus
    decision_criterion: CriterionStatus
    overall_operational_quantum_advantage: CriterionStatus
    probability_one: float
    beta: float
    classical_value: float
    ideal_quantum_value: float
    noisy_quantum_value: float
    ideal_gap: float
    noisy_gap: float
    epsilon_ghz: float
    epsilon_meas: float
    combined_infidelity: float
    epsilon_threshold: float | None
    statistics_method: str
    alpha: float
    n_req: int | None
    expected_wins_at_n_req: int | None
    p_value_at_n_req: float | None
    t_env: float
    r_req: float | None
    r_ghz: float
    tau_dec: float
    t_loc: float
    t_comm: float

    def to_dict(self) -> dict[str, object]:
        output = asdict(self)
        for key, value in tuple(output.items()):
            if isinstance(value, Enum):
                output[key] = value.value
        return output


def evaluate_three_party_operational_advantage(
    *,
    probability_one: float,
    beta: float,
    epsilon_ghz: float,
    epsilon_meas: float,
    alpha: float,
    t_env: float,
    r_ghz: float,
    tau_rot: float,
    tau_meas: float,
    t_loc: float,
    t_comm: float,
    max_rounds: int = 100_000_000,
    chunk_size: int = 32_768,
) -> MultipartyOperationalStatus:
    """Evaluate the Li operational criteria for the Eq. 65 three-party game."""

    probability = _probability("probability_one", probability_one)
    softness = _probability("beta", beta)
    state_error = _probability("epsilon_ghz", epsilon_ghz)
    measurement_error = _probability("epsilon_meas", epsilon_meas)
    significance = _probability("alpha", alpha, strict=True)
    stationary_window = _finite_nonnegative("t_env", t_env)
    if stationary_window == 0.0:
        raise ValueError("t_env must be positive")
    ghz_rate = _finite_nonnegative("r_ghz", r_ghz)
    communication_time = _finite_nonnegative("t_comm", t_comm)
    decision = DecisionCriterion(tau_rot=tau_rot, tau_meas=tau_meas, t_loc=t_loc)

    values = three_party_values(probability, softness)
    epsilon = combined_ghz_infidelity(state_error, measurement_error)
    noisy_value = noisy_three_party_quantum_value(epsilon, values.quantum_value)
    noisy_gap = noisy_value - values.classical_value
    theoretical = values.gap > 0.0
    threshold = (
        three_party_fidelity_threshold(
            values.classical_value, values.quantum_value
        )
        if values.quantum_value > 0.5
        else None
    )
    fidelity_passes = (
        theoretical and threshold is not None and epsilon < threshold
    )

    n_req: int | None = None
    expected_wins: int | None = None
    p_value: float | None = None
    r_req: float | None = None
    statistical_passes = False
    rate_passes = False
    if fidelity_passes:
        n_req = required_trials(
            values.classical_value,
            noisy_value,
            significance,
            max_rounds=max_rounds,
            chunk_size=chunk_size,
        )
        expected_wins = expected_win_count(n_req, noisy_value)
        p_value = certification_p_value(
            n_req, values.classical_value, noisy_value
        )
        statistical_passes = p_value < significance
        r_req = required_trial_rate(n_req, stationary_window)
        rate_passes = statistical_passes and ghz_rate > r_req

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
    status = CriterionStatus.from_condition
    return MultipartyOperationalStatus(
        latency_constrained_regime=status(latency_passes),
        theoretical_advantage=status(theoretical),
        fidelity_criterion=status(fidelity_passes),
        statistical_certification=status(statistical_passes),
        rate_criterion=status(rate_passes),
        decision_criterion=decision.status,
        overall_operational_quantum_advantage=status(overall),
        probability_one=probability,
        beta=softness,
        classical_value=values.classical_value,
        ideal_quantum_value=values.quantum_value,
        noisy_quantum_value=noisy_value,
        ideal_gap=values.gap,
        noisy_gap=noisy_gap,
        epsilon_ghz=state_error,
        epsilon_meas=measurement_error,
        combined_infidelity=epsilon,
        epsilon_threshold=threshold,
        statistics_method="exact_binomial",
        alpha=significance,
        n_req=n_req,
        expected_wins_at_n_req=expected_wins,
        p_value_at_n_req=p_value,
        t_env=stationary_window,
        r_req=r_req,
        r_ghz=ghz_rate,
        tau_dec=decision.tau_dec,
        t_loc=decision.t_loc,
        t_comm=communication_time,
    )
