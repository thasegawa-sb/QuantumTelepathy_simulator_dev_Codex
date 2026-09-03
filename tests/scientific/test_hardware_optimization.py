import pytest

import quantum_telepathy.optimization.hardware as hardware_module
from quantum_telepathy.core.xor_game import (
    independent_bernoulli_distribution,
    uniform_distribution,
)
from quantum_telepathy.hardware.yb_node import YbSystemLevelParameters
from quantum_telepathy.li2026.operational import CriterionStatus
from quantum_telepathy.optimization.hardware import (
    HardwareImprovementDesign,
    HardwareOptimizationScenario,
    HardwareSearchSpace,
    HardwareSearchStatus,
    apply_hardware_improvements,
    classify_search_status,
    direct_operational_reevaluation,
    nondominated_indices,
    search_hardware_designs,
)


def _baseline(**overrides):
    values = {
        "internal_cooperativity": 20.0,
        "n_memory_qubits": 250,
        "n_channels": 1,
        "photon_emission_probability": 0.70,
        "photon_pulse_duration": 240e-9,
        "swap_time": 100e-9,
        "rotation_time": 100e-9,
        "measurement_time": 870e-9,
        "reset_time": 1e-6,
        "memory_lifetime": 7.9,
        "distance_km": 50.0,
        "attenuation_db_per_km": 0.25,
        "group_velocity_m_per_s": 2.1e8,
        "detector_efficiency": 0.9,
        "optics_efficiency": 0.8,
        "dark_count_rate": 10.0,
        "state_infidelity_upper_bound": 0.04,
        "measurement_infidelity": 0.002,
        "link_transmission_override": 0.06,
        "link_latency_override": 240e-6,
    }
    values.update(overrides)
    return YbSystemLevelParameters(**values)


def _scenario(**overrides):
    values = {
        "scenario_id": "ding_rate_stress",
        "ding_p": 0.3,
        "ding_beta": 0.3,
        "input_distribution": independent_bernoulli_distribution(0.3),
        "beta1": 0.3,
        "beta2": 0.3,
        "statistics_method": "general_score_bound",
        "alpha": 0.05,
        "t_env": 1.0,
        "t_loc": 10e-6,
    }
    values.update(overrides)
    return HardwareOptimizationScenario(**values)


def _small_space(**overrides):
    values = {
        "state_infidelity_scales": (0.5, 1.0),
        "measurement_infidelity_scales": (1.0,),
        "detector_headroom_fractions": (0.0,),
        "optics_headroom_fractions": (0.0,),
        "decision_time_scales": (1.0,),
        "memory_lifetime_multipliers": (1.0,),
        "n_memory_qubits": (250, 419),
        "n_channels": (1, 16),
    }
    values.update(overrides)
    return HardwareSearchSpace(**values)


def test_improvement_mapping_uses_distance_laws_and_preserves_layering():
    parameters = apply_hardware_improvements(
        _baseline(),
        HardwareImprovementDesign(
            state_infidelity_scale=0.5,
            measurement_infidelity_scale=0.25,
            detector_headroom_fraction=0.5,
            optics_headroom_fraction=0.5,
            decision_time_scale=0.5,
            memory_lifetime_multiplier=2.0,
            n_memory_qubits=419,
            n_channels=4,
        ),
        75.0,
    )

    assert parameters.state_infidelity_upper_bound == pytest.approx(0.02)
    assert parameters.measurement_infidelity == pytest.approx(0.0005)
    assert parameters.detector_efficiency == pytest.approx(0.95)
    assert parameters.optics_efficiency == pytest.approx(0.9)
    assert parameters.rotation_time == pytest.approx(50e-9)
    assert parameters.measurement_time == pytest.approx(435e-9)
    assert parameters.memory_lifetime == pytest.approx(15.8)
    assert parameters.n_memory_qubits == 419
    assert parameters.n_channels == 4
    assert parameters.distance_km == 75.0
    assert parameters.link_transmission_override is None
    assert parameters.link_latency_override is None


def test_finite_search_finds_rate_and_fidelity_tradeoff():
    result = search_hardware_designs(
        baseline=_baseline(),
        scenario=_scenario(),
        distance_km=50.0,
        search_space=_small_space(),
    )

    assert result.search_method == "exhaustive_finite_grid"
    assert result.candidate_count == 8
    assert result.evaluated_count == 8
    assert result.evaluation_error_count == 0
    assert result.search_status is HardwareSearchStatus.FEASIBLE
    assert result.baseline is not None
    assert result.baseline.constraint_violations == ("rate_criterion",)
    assert result.feasible_count == 6
    assert result.pareto_count == 2
    assert result.recommended is not None
    assert result.recommended.changed_lever_count == 1


def test_game_values_are_computed_once_per_hardware_search(monkeypatch):
    original = hardware_module.generalized_lctc_values
    call_count = 0

    def counted_values(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(hardware_module, "generalized_lctc_values", counted_values)

    result = search_hardware_designs(
        baseline=_baseline(),
        scenario=_scenario(),
        distance_km=50.0,
        search_space=_small_space(),
    )

    assert result.evaluated_count == 8
    assert call_count == 1


def test_selected_candidate_matches_direct_phase11_operational_reevaluation():
    result = search_hardware_designs(
        baseline=_baseline(),
        scenario=_scenario(),
        distance_km=50.0,
        search_space=_small_space(),
    )
    candidate = result.recommended
    assert candidate is not None

    direct = direct_operational_reevaluation(candidate, _scenario())

    assert direct.n_req == candidate.n_req
    assert direct.r_req == pytest.approx(candidate.r_req)
    assert direct.epsilon == pytest.approx(candidate.epsilon)
    assert direct.r_heg == pytest.approx(candidate.r_heg)
    assert direct.tau_dec == pytest.approx(candidate.tau_dec)
    assert (
        direct.overall_operational_quantum_advantage
        is candidate.overall_operational_quantum_advantage
        is CriterionStatus.PASS
    )


def test_baseline_feasible_is_distinct_from_improvement_required():
    scenario = _scenario(
        scenario_id="chsh_baseline",
        ding_p=0.5,
        ding_beta=0.0,
        input_distribution=uniform_distribution(),
        beta1=0.0,
        beta2=0.0,
        statistics_method="exact_binomial",
    )
    result = search_hardware_designs(
        baseline=_baseline(),
        scenario=scenario,
        distance_km=50.0,
        search_space=_small_space(),
    )

    assert result.search_status is HardwareSearchStatus.BASELINE_FEASIBLE
    assert result.baseline is not None
    assert result.baseline.overall_operational_quantum_advantage is CriterionStatus.PASS
    assert result.recommended is not None
    assert result.recommended.weighted_cost == 0.0


def test_no_theoretical_advantage_is_infeasible_not_optimizer_failure():
    scenario = _scenario(
        scenario_id="flat_utility",
        ding_p=0.5,
        ding_beta=0.5,
        input_distribution=uniform_distribution(),
        beta1=0.5,
        beta2=0.5,
        statistics_method="general_score_bound",
    )
    result = search_hardware_designs(
        baseline=_baseline(),
        scenario=scenario,
        distance_km=50.0,
        search_space=_small_space(),
    )

    assert result.search_status is HardwareSearchStatus.INFEASIBLE_SEARCH_SPACE
    assert result.evaluated_count == result.candidate_count
    assert result.evaluation_error_count == 0
    assert result.feasible_count == 0
    assert result.recommended is None
    assert result.baseline is not None
    assert result.baseline.tau_mem_threshold is None
    assert all(
        "theoretical_advantage" in candidate.constraint_violations
        for candidate in result.candidates
    )


def test_tight_decision_window_requires_an_explicit_speed_improvement():
    space = _small_space(decision_time_scales=(0.5, 1.0))
    result = search_hardware_designs(
        baseline=_baseline(),
        scenario=_scenario(t_loc=0.5e-6),
        distance_km=50.0,
        search_space=space,
    )

    assert result.search_status is HardwareSearchStatus.FEASIBLE
    assert result.baseline is not None
    assert "decision_criterion" in result.baseline.constraint_violations
    assert result.recommended is not None
    assert result.recommended.design.decision_time_scale == 0.5
    assert result.recommended.tau_dec == pytest.approx(0.485e-6)


def test_pareto_front_indices_use_minimization_and_keep_tradeoffs():
    vectors = (
        (0.0, 1.0),
        (1.0, 0.0),
        (0.5, 0.5),
        (1.0, 1.0),
        (0.6, 0.6),
    )

    assert nondominated_indices(vectors) == (0, 1, 2)


@pytest.mark.parametrize(
    ("evaluated", "feasible", "baseline", "expected"),
    [
        (1, 1, True, HardwareSearchStatus.BASELINE_FEASIBLE),
        (1, 1, False, HardwareSearchStatus.FEASIBLE),
        (1, 0, False, HardwareSearchStatus.INFEASIBLE_SEARCH_SPACE),
        (0, 0, False, HardwareSearchStatus.EVALUATION_FAILED),
        (0, 0, True, HardwareSearchStatus.BASELINE_FEASIBLE),
    ],
)
def test_search_status_classification(evaluated, feasible, baseline, expected):
    assert (
        classify_search_status(
            evaluated_count=evaluated,
            feasible_count=feasible,
            baseline_feasible=baseline,
        )
        is expected
    )


def test_search_space_is_deduplicated_and_candidate_count_is_exact():
    space = _small_space(
        state_infidelity_scales=(1.0, 0.5, 1.0),
        n_channels=(16, 1, 16),
    )

    assert space.state_infidelity_scales == (0.5, 1.0)
    assert space.n_channels == (1, 16)
    assert space.candidate_count == 8
    assert len(tuple(space.designs())) == 8


@pytest.mark.parametrize(
    "overrides",
    [
        {"state_infidelity_scale": 0.0},
        {"measurement_infidelity_scale": 1.1},
        {"detector_headroom_fraction": -0.1},
        {"optics_headroom_fraction": 1.1},
        {"decision_time_scale": 0.0},
        {"memory_lifetime_multiplier": 0.9},
        {"n_memory_qubits": 0},
        {"n_channels": True},
    ],
)
def test_improvement_design_rejects_invalid_values(overrides):
    values = {"n_memory_qubits": 250, "n_channels": 1}
    values.update(overrides)
    with pytest.raises(ValueError):
        HardwareImprovementDesign(**values)


def test_search_rejects_resource_counts_below_baseline():
    with pytest.raises(ValueError):
        search_hardware_designs(
            baseline=_baseline(),
            scenario=_scenario(),
            distance_km=50.0,
            search_space=_small_space(n_memory_qubits=(249,)),
        )


def test_search_requires_the_unchanged_baseline_in_the_design_lattice():
    with pytest.raises(ValueError, match="unchanged baseline"):
        search_hardware_designs(
            baseline=_baseline(),
            scenario=_scenario(),
            distance_km=50.0,
            search_space=_small_space(state_infidelity_scales=(0.5,)),
        )
