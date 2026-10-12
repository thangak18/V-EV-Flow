"""Stateful five-minute charging simulation.

Events at one timestamp apply in a fixed order: repairs, faults, completions,
arrivals, queue admission, snapshot. A port that breaks while every healthy
port is busy interrupts the session with the most remaining time (ties broken
by vehicle id); that vehicle returns to the front of the queue with its
remaining minutes, so no vehicle is lost.
"""

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timedelta

from app.backend.contracts.enums import Scenario
from app.backend.contracts.simulation import BackgroundArrival, PortEvent, ScenarioConfig
from app.backend.contracts.stations import Station
from app.backend.modules.simulation.domain import (
    ChargingSession,
    QueuedVehicle,
    StationRuntimeState,
    StationSnapshot,
    StepSnapshot,
)


class SimulationEngine:
    def __init__(
        self,
        stations: Sequence[Station],
        scenario: Scenario,
        arrivals: Sequence[BackgroundArrival] = (),
        service_durations: Sequence[float] = (),
        port_events: Sequence[PortEvent] = (),
    ) -> None:
        if len(arrivals) != len(service_durations):
            raise ValueError("one service duration is required per background arrival")
        self._scenario = scenario
        self._states = {
            item.station_id: StationRuntimeState(item.station_id, item.n_ports) for item in stations
        }
        if len(self._states) != len(stations):
            raise ValueError("station_id values must be unique")
        self._pending: dict[str, list[QueuedVehicle]] = defaultdict(list)
        self._arrivals = sorted(
            zip(arrivals, service_durations, strict=True), key=lambda x: x[0].ts
        )
        self._port_events = sorted(port_events, key=lambda item: item.ts)
        self._arrival_index = 0
        self._event_index = 0
        self._last_ts: datetime | None = None

    def arrive(self, vehicle_id: str, station_id: str, service_minutes: float) -> None:
        """Queue a vehicle to be admitted at the next step."""
        if station_id not in self._states:
            raise KeyError(station_id)
        if service_minutes <= 0:
            raise ValueError("service_minutes must be positive")
        self._pending[station_id].append(QueuedVehicle(vehicle_id, service_minutes))

    def step(self, ts: datetime) -> StepSnapshot:
        if self._last_ts is not None and ts <= self._last_ts:
            raise ValueError("steps must advance in time")
        self._last_ts = ts
        due_events = self._take_due_events(ts)
        for event in due_events:
            if event.ports_delta > 0:
                self._repair(event)
        for event in due_events:
            if event.ports_delta < 0:
                self._fault(event, ts)
        for state in self._states.values():
            state.sessions = [item for item in state.sessions if item.ends_at > ts]
        self._take_due_arrivals(ts)
        for station_id, vehicles in self._pending.items():
            self._states[station_id].queue.extend(vehicles)
        self._pending.clear()
        for state in self._states.values():
            self._admit(state, ts)
        return self._snapshot(ts)

    def run(self, config: ScenarioConfig) -> tuple[StepSnapshot, ...]:
        step = timedelta(minutes=config.step_minutes)
        snapshots: list[StepSnapshot] = []
        ts = config.start
        while ts <= config.end:
            snapshots.append(self.step(ts))
            ts += step
        return tuple(snapshots)

    def _take_due_events(self, ts: datetime) -> list[PortEvent]:
        start = self._event_index
        while (
            self._event_index < len(self._port_events)
            and self._port_events[self._event_index].ts <= ts
        ):
            self._event_index += 1
        return self._port_events[start : self._event_index]

    def _take_due_arrivals(self, ts: datetime) -> None:
        while (
            self._arrival_index < len(self._arrivals)
            and self._arrivals[self._arrival_index][0].ts <= ts
        ):
            arrival, minutes = self._arrivals[self._arrival_index]
            self._arrival_index += 1
            self._states[arrival.station_id].queue.append(
                QueuedVehicle(arrival.vehicle_id, minutes)
            )

    def _repair(self, event: PortEvent) -> None:
        state = self._states[event.station_id]
        state.broken = max(0, state.broken - event.ports_delta)

    def _fault(self, event: PortEvent, ts: datetime) -> None:
        state = self._states[event.station_id]
        for _ in range(-event.ports_delta):
            if state.broken >= state.n_ports:
                return
            if state.free == 0:
                victim = max(state.sessions, key=lambda s: (s.ends_at, s.vehicle_id))
                state.sessions.remove(victim)
                remaining = (victim.ends_at - ts).total_seconds() / 60
                state.queue.insert(0, QueuedVehicle(victim.vehicle_id, remaining))
            state.broken += 1

    def _admit(self, state: StationRuntimeState, ts: datetime) -> None:
        while state.queue and state.free > 0:
            vehicle = state.queue.pop(0)
            end = ts + timedelta(minutes=vehicle.service_minutes)
            state.sessions.append(
                ChargingSession(vehicle.vehicle_id, ts, end, vehicle.service_minutes)
            )

    def _snapshot(self, ts: datetime) -> StepSnapshot:
        stations = []
        for state in self._states.values():
            if (
                min(state.free, state.busy, state.broken) < 0
                or state.free + state.busy + state.broken != state.n_ports
            ):
                raise RuntimeError(f"port conservation violated at {state.station_id} {ts}")
            stations.append(
                StationSnapshot(
                    station_id=state.station_id,
                    ports_free=state.free,
                    ports_busy=state.busy,
                    ports_broken=state.broken,
                    n_ports=state.n_ports,
                    queue_length=len(state.queue),
                    active_vehicle_ids=frozenset(item.vehicle_id for item in state.sessions),
                )
            )
        return StepSnapshot(ts=ts, scenario=self._scenario, stations=tuple(stations))
