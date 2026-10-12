from datetime import datetime, timedelta, timezone

import pytest

from app.backend.contracts.enums import Scenario
from app.backend.contracts.simulation import BackgroundArrival, PortEvent, ScenarioConfig
from app.backend.contracts.stations import Station
from app.backend.modules.simulation.engine import SimulationEngine

T0 = datetime(2026, 10, 13, 8, 0, tzinfo=timezone(timedelta(hours=7)))
STEP = timedelta(minutes=5)


def make_station(station_id: str = "S001", n_ports: int = 1) -> Station:
    return Station(
        station_id=station_id,
        name="Test",
        lat=10.0,
        lng=106.0,
        n_ports=n_ports,
        power_kw=60.0,
        connector_types=["CCS2"],
        network="test",
        station_type="urban",
        source="test",
        assumptions=["test"],
    )


def make_engine(n_ports: int = 1, **kwargs) -> SimulationEngine:  # noqa: ANN003
    return SimulationEngine([make_station(n_ports=n_ports)], Scenario.NORMAL, **kwargs)


def test_session_remains_busy_until_service_end() -> None:
    engine = make_engine()
    engine.arrive("V001", "S001", service_minutes=15)
    states = [engine.step(T0 + i * STEP).station("S001") for i in range(4)]
    assert [item.ports_busy for item in states] == [1, 1, 1, 0]
    assert states[-1].ports_free == 1


def test_waiting_vehicle_enters_when_port_is_released_in_fifo_order() -> None:
    engine = make_engine()
    engine.arrive("V001", "S001", service_minutes=5)
    engine.arrive("V002", "S001", service_minutes=10)
    engine.arrive("V003", "S001", service_minutes=5)
    first = engine.step(T0)
    assert first.active_vehicle_ids == {"V001"}
    assert first.station("S001").queue_length == 2
    assert engine.step(T0 + STEP).active_vehicle_ids == {"V002"}
    assert engine.step(T0 + 2 * STEP).active_vehicle_ids == {"V002"}
    assert engine.step(T0 + 3 * STEP).active_vehicle_ids == {"V003"}


def test_broken_port_stays_broken_until_repaired_and_keeps_charging_vehicle() -> None:
    events = [
        PortEvent(station_id="S001", ts=T0 + STEP, ports_delta=-1),
        PortEvent(station_id="S001", ts=T0 + 3 * STEP, ports_delta=1),
    ]
    engine = make_engine(n_ports=2, port_events=events)
    engine.arrive("V001", "S001", service_minutes=60)
    engine.arrive("V002", "S001", service_minutes=60)
    snapshots = [engine.step(T0 + i * STEP).station("S001") for i in range(5)]
    assert [item.ports_broken for item in snapshots] == [0, 1, 1, 0, 0]
    # The fault interrupts one session; both vehicles are still in the system.
    for item in snapshots:
        assert len(item.active_vehicle_ids) + item.queue_length == 2
    assert snapshots[1].queue_length == 1
    assert snapshots[3].active_vehicle_ids == {"V001", "V002"}


def test_fault_prefers_free_port_over_interrupting_a_session() -> None:
    engine = make_engine(
        n_ports=2, port_events=[PortEvent(station_id="S001", ts=T0 + STEP, ports_delta=-1)]
    )
    engine.arrive("V001", "S001", service_minutes=60)
    engine.step(T0)
    after = engine.step(T0 + STEP).station("S001")
    assert (after.ports_free, after.ports_busy, after.ports_broken) == (0, 1, 1)
    assert after.queue_length == 0


def test_interrupted_vehicle_resumes_with_remaining_time() -> None:
    engine = make_engine(
        port_events=[
            PortEvent(station_id="S001", ts=T0 + STEP, ports_delta=-1),
            PortEvent(station_id="S001", ts=T0 + 2 * STEP, ports_delta=1),
        ]
    )
    engine.arrive("V001", "S001", service_minutes=15)
    snapshots = [engine.step(T0 + i * STEP).station("S001") for i in range(5)]
    # Charged 5 min, interrupted at +5, repaired at +10 (admitted), 10 min left -> done at +20.
    assert [item.ports_busy for item in snapshots] == [1, 0, 1, 1, 0]


def test_conservation_holds_for_every_step_of_a_random_run() -> None:
    arrivals = [
        BackgroundArrival(station_id="S001", ts=T0 + (i // 3) * STEP, vehicle_id=f"B{i}")
        for i in range(60)
    ]
    events = [
        PortEvent(station_id="S001", ts=T0 + i * STEP, ports_delta=-1 if i % 4 == 1 else 1)
        for i in range(1, 40)
    ]
    engine = make_engine(
        n_ports=3, arrivals=arrivals, service_durations=[17.0] * 60, port_events=events
    )
    config = ScenarioConfig(
        scenario=Scenario.NORMAL,
        seed=1,
        start=T0,
        end=T0 + 60 * STEP,
        step_minutes=5,
        demand_multiplier=1.0,
        compliance_rate=0.7,
    )
    for snapshot in engine.run(config):
        item = snapshot.station("S001")
        assert min(item.ports_free, item.ports_busy, item.ports_broken) >= 0
        assert item.ports_free + item.ports_busy + item.ports_broken == item.n_ports


def test_queue_continues_across_steps_without_free_port() -> None:
    arrivals = [BackgroundArrival(station_id="S001", ts=T0, vehicle_id=f"B{i}") for i in range(3)]
    engine = make_engine(arrivals=arrivals, service_durations=[10.0] * 3)
    lengths = [engine.step(T0 + i * STEP).station("S001").queue_length for i in range(6)]
    assert lengths == [2, 2, 1, 1, 0, 0]


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="duration"):
        make_engine(arrivals=[BackgroundArrival(station_id="S001", ts=T0, vehicle_id="B")])
    with pytest.raises(ValueError, match="unique"):
        SimulationEngine([make_station(), make_station()], Scenario.NORMAL)
    engine = make_engine()
    with pytest.raises(KeyError):
        engine.arrive("V", "S999", 5)
    with pytest.raises(ValueError, match="positive"):
        engine.arrive("V", "S001", 0)
    engine.step(T0)
    with pytest.raises(ValueError, match="advance"):
        engine.step(T0)
