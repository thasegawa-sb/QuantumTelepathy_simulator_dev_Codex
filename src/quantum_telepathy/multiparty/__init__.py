"""Generic multiparty nonlocal-game primitives."""

from quantum_telepathy.multiparty.xor import (
    GHZOptimizationResult,
    MultipartyClassicalBiasResult,
    binary_input_tuples,
    deterministic_classical_bias,
    ghz_bias_at_phases,
    independent_bernoulli_distribution,
    optimize_ghz_equatorial_bias,
    symmetric_ghz_equatorial_bias,
    validate_binary_input_distribution,
    xor_coefficients,
)

__all__ = [
    "binary_input_tuples",
    "deterministic_classical_bias",
    "GHZOptimizationResult",
    "ghz_bias_at_phases",
    "independent_bernoulli_distribution",
    "MultipartyClassicalBiasResult",
    "optimize_ghz_equatorial_bias",
    "symmetric_ghz_equatorial_bias",
    "validate_binary_input_distribution",
    "xor_coefficients",
]
