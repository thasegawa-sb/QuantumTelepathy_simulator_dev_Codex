"""Ding-Jiang arXiv:2407.21723v3 reproduction helpers."""

from quantum_telepathy.ding_jiang.fig3 import (
    Fig3Point,
    evaluate_fig3_grid,
    evaluate_fig3_point,
    independent_classical_value,
)
from quantum_telepathy.ding_jiang.hft import (
    biased_chsh_values,
    hedging_matrix,
    hedging_utility,
    ideal_hedging_values,
)
from quantum_telepathy.ding_jiang.loss import (
    LossThresholdResult,
    LossyOptimizationResult,
    find_loss_threshold,
    lossy_bell_operator,
    lossy_expected_utility,
    optimize_lossy_value,
    projective_measurement,
    schmidt_coefficients,
)

__all__ = [
    "Fig3Point",
    "LossThresholdResult",
    "LossyOptimizationResult",
    "biased_chsh_values",
    "evaluate_fig3_grid",
    "evaluate_fig3_point",
    "hedging_matrix",
    "hedging_utility",
    "independent_classical_value",
    "ideal_hedging_values",
    "find_loss_threshold",
    "lossy_bell_operator",
    "lossy_expected_utility",
    "optimize_lossy_value",
    "projective_measurement",
    "schmidt_coefficients",
]
