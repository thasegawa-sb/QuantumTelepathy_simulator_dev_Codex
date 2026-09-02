import math
from dataclasses import asdict

import pytest

from quantum_telepathy.hardware.event_simulation import (
    M2EventSimulationParameters,
    M2EventType,
    simulate_m2_memory_bank,
)


def _parameters(**overrides):
    values = {
        "tau_e": 1.0,
        "tau_link": 2.0,
        "tau_dec": 0.5,
        "tau_res": 0.5,
        "n_memory_qubits": 2,
        "entanglement_success_probability": 1.0,
        "measurement_duration": 20.0,
        "warmup_duration": 8.0,
        "seed": 260407451,
        "trace_attempts": 2,
    }
    values.update(overrides)
    return M2EventSimulationParameters(**values)


def test_memory_limited_schedule_matches_equations_46_to_48_exactly():
    result = simulate_m2_memory_bank(_parameters())

    assert result.tau_occ == 4.0
    assert result.attempts_launched == 10
    assert result.heralded_trials == 10
    assert result.successful_heralds == 10
    assert result.attempt_rate == 0.5
    assert result.heralded_trial_rate == 0.5
    assert result.bell_pair_rate == 0.5
    assert result.empirical_success_probability == 1.0
    assert result.mean_occupied_memories == 2.0
    assert result.occupied_memories_std == 0.0
    assert result.peak_occupied_memories == 2
    assert [asdict(item) for item in result.occupancy_time_distribution] == [
        {"occupied_memories": 2, "duration": 20.0, "fraction": 1.0}
    ]
    assert result.memory_wait_launches > 0
    assert result.emitter_memory_wait_time > 0.0


def test_channel_limited_schedule_matches_one_over_tau_e_and_littles_law():
    result = simulate_m2_memory_bank(_parameters(n_memory_qubits=5))

    assert result.attempt_rate == 1.0
    assert result.heralded_trial_rate == 1.0
    assert result.mean_occupied_memories == 4.0
    assert result.occupied_memories_std == 0.0
    assert result.peak_occupied_memories == 4
    assert result.occupancy_time_distribution[0].occupied_memories == 4
    assert result.occupancy_time_distribution[0].fraction == 1.0
    assert result.memory_wait_launches == 0
    assert result.emitter_memory_wait_time == 0.0


def test_trace_separates_attempt_herald_and_memory_release_events():
    result = simulate_m2_memory_bank(_parameters())

    assert len(result.trace) == 6
    assert [event.time for event in result.trace] == sorted(
        event.time for event in result.trace
    )
    assert {event.event_type for event in result.trace} == {
        M2EventType.ATTEMPT_START,
        M2EventType.HERALD_SUCCESS,
        M2EventType.MEMORY_RELEASE,
    }
    for attempt_id in (0, 1):
        selected = [
            event for event in result.trace if event.attempt_id == attempt_id
        ]
        assert [event.event_type for event in selected] == [
            M2EventType.ATTEMPT_START,
            M2EventType.HERALD_SUCCESS,
            M2EventType.MEMORY_RELEASE,
        ]
        assert selected[1].time - selected[0].time == 3.0
        assert selected[2].time - selected[0].time == 4.0


def test_seeded_bernoulli_stream_is_reproducible():
    first = simulate_m2_memory_bank(
        _parameters(entanglement_success_probability=0.3, trace_attempts=0)
    )
    second = simulate_m2_memory_bank(
        _parameters(entanglement_success_probability=0.3, trace_attempts=0)
    )

    assert first.successful_heralds == second.successful_heralds
    assert first.heralded_trials == second.heralded_trials
    assert first.bell_pair_rate == second.bell_pair_rate
    assert first.mean_occupied_memories == second.mean_occupied_memories


@pytest.mark.parametrize(
    ("probability", "expected_successes"),
    [(0.0, 0), (1.0, 10)],
)
def test_success_probability_limits(probability, expected_successes):
    result = simulate_m2_memory_bank(
        _parameters(entanglement_success_probability=probability)
    )

    assert result.successful_heralds == expected_successes


def test_window_without_herald_arrivals_reports_undefined_empirical_probability():
    result = simulate_m2_memory_bank(
        _parameters(
            warmup_duration=0.0,
            measurement_duration=0.5,
            trace_attempts=0,
        )
    )

    assert result.heralded_trials == 0
    assert result.empirical_success_probability is None
    assert result.bell_pair_rate == 0.0


@pytest.mark.parametrize(
    ("overrides", "exception"),
    [
        ({"tau_e": 0.0}, ValueError),
        ({"tau_link": -1.0}, ValueError),
        ({"n_memory_qubits": 0}, ValueError),
        ({"n_memory_qubits": 1.5}, TypeError),
        ({"entanglement_success_probability": 1.1}, ValueError),
        ({"measurement_duration": 0.0}, ValueError),
        ({"warmup_duration": math.inf}, ValueError),
        ({"seed": -1}, ValueError),
        ({"trace_attempts": True}, TypeError),
    ],
)
def test_event_simulation_rejects_invalid_parameters(overrides, exception):
    with pytest.raises(exception):
        _parameters(**overrides)
