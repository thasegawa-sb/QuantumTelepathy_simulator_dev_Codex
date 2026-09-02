"""Li et al. arXiv:2604.07451v1 reproduction helpers."""

from quantum_telepathy.li2026.fidelity import (
    combined_infidelity,
    combined_infidelity_small_error_approx,
    fidelity_threshold,
    measurement_visibility,
    noisy_gap,
    noisy_quantum_value,
    noisy_singlet_correlator,
    singlet_density_matrix,
    werner_state,
)
from quantum_telepathy.li2026.lctc import (
    check_latency_constraint,
    correlated_input_distribution,
    enumerated_classical_optimum,
    generalized_lctc_matrix,
    generalized_lctc_utility,
    generalized_lctc_values,
)
from quantum_telepathy.li2026.statistics import (
    CertificationSearchLimitError,
    NoFiniteCertificationError,
    binomial_tail_p_value,
    certification_p_value,
    expected_win_count,
    required_rate,
    required_trial_rate,
    required_trials,
    required_trials_sequence,
)

__all__ = [
    "check_latency_constraint",
    "CertificationSearchLimitError",
    "combined_infidelity",
    "combined_infidelity_small_error_approx",
    "correlated_input_distribution",
    "enumerated_classical_optimum",
    "fidelity_threshold",
    "generalized_lctc_matrix",
    "generalized_lctc_utility",
    "generalized_lctc_values",
    "measurement_visibility",
    "NoFiniteCertificationError",
    "noisy_gap",
    "noisy_quantum_value",
    "noisy_singlet_correlator",
    "singlet_density_matrix",
    "binomial_tail_p_value",
    "certification_p_value",
    "expected_win_count",
    "required_rate",
    "required_trial_rate",
    "required_trials",
    "required_trials_sequence",
    "werner_state",
]
