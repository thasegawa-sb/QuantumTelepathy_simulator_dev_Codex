"""Core nonlocal-game and XOR-game primitives."""

from quantum_telepathy.core.classical import (
    ClassicalOptimizationResult,
    deterministic_joint_strategies,
    deterministic_strategy_value,
    maximize_classical_value,
)
from quantum_telepathy.core.xor_game import (
    Matrix2x2,
    ParityUtility2x2,
    chsh_matrix,
    chsh_values,
    classical_bias,
    classical_value,
    gap,
    independent_bernoulli_distribution,
    quantum_bias_2x2,
    quantum_value,
    uniform_distribution,
    xor_game_matrix,
)

__all__ = [
    "ClassicalOptimizationResult",
    "Matrix2x2",
    "ParityUtility2x2",
    "chsh_matrix",
    "chsh_values",
    "classical_bias",
    "classical_value",
    "deterministic_joint_strategies",
    "deterministic_strategy_value",
    "gap",
    "independent_bernoulli_distribution",
    "maximize_classical_value",
    "quantum_bias_2x2",
    "quantum_value",
    "uniform_distribution",
    "xor_game_matrix",
]
