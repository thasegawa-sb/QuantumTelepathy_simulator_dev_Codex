"""Platform-independent quantum-network hardware models."""

from quantum_telepathy.hardware.heg import (
    HEGRateParameters,
    HEGRateResult,
    evaluate_heg_rate,
    heralded_entanglement_generation_rate,
    meets_heg_rate_criterion,
)
from quantum_telepathy.hardware.memory_m0_m1_m2 import (
    M2MemoryFidelityResult,
    M2TimingParameters,
    M2TimingResult,
    MemoryArchitecture,
    evaluate_m2_memory_fidelity,
    evaluate_m2_timing,
    heg_attempt_rate,
    memory_adjusted_state_infidelity,
    memory_depth_saturates,
    memory_lifetime_threshold,
    minimum_memory_qubits,
    occupancy_time,
)

__all__ = [
    "evaluate_heg_rate",
    "evaluate_m2_memory_fidelity",
    "evaluate_m2_timing",
    "HEGRateParameters",
    "HEGRateResult",
    "heg_attempt_rate",
    "heralded_entanglement_generation_rate",
    "M2MemoryFidelityResult",
    "M2TimingParameters",
    "M2TimingResult",
    "meets_heg_rate_criterion",
    "memory_adjusted_state_infidelity",
    "MemoryArchitecture",
    "memory_depth_saturates",
    "memory_lifetime_threshold",
    "minimum_memory_qubits",
    "occupancy_time",
]
