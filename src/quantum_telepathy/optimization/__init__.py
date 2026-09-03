"""Configuration-driven hardware-resource optimization."""

from quantum_telepathy.optimization.hardware import (
    HardwareCandidateEvaluation,
    HardwareCostVector,
    HardwareImprovementDesign,
    HardwareOptimizationScenario,
    HardwareSearchResult,
    HardwareSearchSpace,
    HardwareSearchStatus,
    apply_hardware_improvements,
    classify_search_status,
    direct_operational_reevaluation,
    nondominated_indices,
    search_hardware_designs,
)

__all__ = [
    "HardwareCandidateEvaluation",
    "HardwareCostVector",
    "HardwareImprovementDesign",
    "HardwareOptimizationScenario",
    "HardwareSearchResult",
    "HardwareSearchSpace",
    "HardwareSearchStatus",
    "apply_hardware_improvements",
    "classify_search_status",
    "direct_operational_reevaluation",
    "nondominated_indices",
    "search_hardware_designs",
]
