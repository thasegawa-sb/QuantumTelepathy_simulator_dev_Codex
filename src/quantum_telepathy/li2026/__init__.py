"""Li et al. arXiv:2604.07451v1 reproduction helpers."""

from quantum_telepathy.li2026.fidelity import (
    combined_infidelity,
    combined_infidelity_small_error_approx,
    fidelity_threshold,
    noisy_gap,
    noisy_quantum_value,
)
from quantum_telepathy.li2026.lctc import (
    check_latency_constraint,
    generalized_lctc_matrix,
    generalized_lctc_utility,
)

__all__ = [
    "check_latency_constraint",
    "combined_infidelity",
    "combined_infidelity_small_error_approx",
    "fidelity_threshold",
    "generalized_lctc_matrix",
    "generalized_lctc_utility",
    "noisy_gap",
    "noisy_quantum_value",
]
