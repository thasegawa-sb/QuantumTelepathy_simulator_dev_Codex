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

__all__ = [
    "check_latency_constraint",
    "combined_infidelity",
    "combined_infidelity_small_error_approx",
    "correlated_input_distribution",
    "enumerated_classical_optimum",
    "fidelity_threshold",
    "generalized_lctc_matrix",
    "generalized_lctc_utility",
    "generalized_lctc_values",
    "measurement_visibility",
    "noisy_gap",
    "noisy_quantum_value",
    "noisy_singlet_correlator",
    "singlet_density_matrix",
    "werner_state",
]
