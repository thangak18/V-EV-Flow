"""Deterministic background events and vehicles for one scenario.

One ``numpy`` generator seeded from the scenario drives every random draw, in a
fixed order: vehicles, arrivals, service durations, port faults/repairs. The
resulting ``FixtureBundle`` is immutable input shared by all strategies, so
strategies never touch the RNG.

``PortEvent.ports_delta`` is ``-1`` when a port breaks and ``+1`` when one is
repaired.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta

import numpy as np

from app.backend.contracts.recommendation import Vehicle
from app.backend.contracts.simulation import (
    BackgroundArrival,
    FixtureBundle,
    PortEvent,
    ScenarioConfig,
)
from app.backend.contracts.stations import Station
from app.backend.modules.station_data.loaders import ScenarioSpec

# Mean background arrivals per port per hour before coefficients (assumption).
BASE_ARRIVALS_PER_PORT_HOUR = 0.35
_BATTERY_KWH = (42.0, 60.0, 75.0, 82.0)
_DAY_NAMES = ("weekday", "weekday", "weekday", "weekday", "weekday", "saturday", "sunday")


def step_times(config: ScenarioConfig) -> list[datetime]:
    step = timedelta(minutes=config.step_minutes)
    count = int((config.end - config.start) / step) + 1
    return [config.start + index * step for index in range(count)]


def _hour_coefficient(spec: ScenarioSpec, hour: int) -> float:
    start_hour = max(key for key in spec.hour_coefficients if key <= hour)
    return spec.hour_coefficients[start_hour]


def _arrival_rates(spec: ScenarioSpec, times: Sequence[datetime], stations: Sequence[Station]):
    """Expected arrivals per step, shape (steps, stations)."""
    step_hours = spec.step_minutes / 60
    time_factor = np.array(
        [
            _hour_coefficient(spec, ts.hour) * spec.day_coefficients[_DAY_NAMES[ts.weekday()]]
            for ts in times
        ]
    )
    station_factor = np.array(
        [
            station.n_ports
            * BASE_ARRIVALS_PER_PORT_HOUR
            * spec.station_type_coefficients.get(station.station_type, 1.0)
            for station in stations
        ]
    )
    scale = spec.arrival_multiplier * spec.holiday_multiplier * step_hours
    return scale * np.outer(time_factor, station_factor)


def _generate_vehicles(rng: np.random.Generator, count: int) -> tuple[Vehicle, ...]:
    soc = rng.uniform(15.0, 80.0, size=count)
    battery = rng.choice(_BATTERY_KWH, size=count)
    consumption = rng.uniform(0.15, 0.22, size=count)
    return tuple(
        Vehicle(
            soc_pct=round(float(s), 1),
            battery_kwh=float(b),
            consumption_kwh_per_km=round(float(c), 3),
            connector_type="CCS2",
        )
        for s, b, c in zip(soc, battery, consumption, strict=True)
    )


def _generate_arrivals(
    rng: np.random.Generator,
    spec: ScenarioSpec,
    times: Sequence[datetime],
    stations: Sequence[Station],
) -> tuple[BackgroundArrival, ...]:
    counts = rng.poisson(_arrival_rates(spec, times, stations))
    arrivals: list[BackgroundArrival] = []
    for step_index, station_index in zip(*np.nonzero(counts), strict=True):
        for _ in range(int(counts[step_index, station_index])):
            arrivals.append(
                BackgroundArrival(
                    station_id=stations[station_index].station_id,
                    ts=times[step_index],
                    vehicle_id=f"B{len(arrivals) + 1:06d}",
                )
            )
    return tuple(arrivals)


def _generate_durations(rng: np.random.Generator, spec: ScenarioSpec, count: int):
    low, high = spec.charging_minutes
    return tuple(round(float(item), 1) for item in rng.uniform(low, high, size=count))


def _generate_port_events(
    rng: np.random.Generator,
    spec: ScenarioSpec,
    times: Sequence[datetime],
    stations: Sequence[Station],
) -> tuple[PortEvent, ...]:
    """Per step, repairs apply before faults; a station never loses more ports than it has."""
    fault_draws = rng.random((len(times), len(stations)))
    repair_draws = rng.random((len(times), len(stations), max(s.n_ports for s in stations)))
    broken = [0] * len(stations)
    events: list[PortEvent] = []
    for step_index, ts in enumerate(times):
        for station_index, station in enumerate(stations):
            repaired = int(
                np.count_nonzero(
                    repair_draws[step_index, station_index, : broken[station_index]]
                    < spec.repair_probability
                )
            )
            events.extend(
                PortEvent(station_id=station.station_id, ts=ts, ports_delta=1)
                for _ in range(repaired)
            )
            broken[station_index] -= repaired
            if (
                broken[station_index] < station.n_ports
                and fault_draws[step_index, station_index] < spec.fault_probability
            ):
                events.append(PortEvent(station_id=station.station_id, ts=ts, ports_delta=-1))
                broken[station_index] += 1
    return tuple(events)


def generate_fixture_bundle(
    spec: ScenarioSpec, stations: Sequence[Station], vehicle_count: int
) -> FixtureBundle:
    if vehicle_count < 0:
        raise ValueError("vehicle_count must be non-negative")
    if not stations:
        raise ValueError("at least one station is required")
    config = spec.to_config()
    times = step_times(config)
    rng = np.random.default_rng(config.seed)
    vehicles = _generate_vehicles(rng, vehicle_count)
    arrivals = _generate_arrivals(rng, spec, times, stations)
    durations = _generate_durations(rng, spec, len(arrivals))
    port_events = _generate_port_events(rng, spec, times, stations)
    return FixtureBundle(
        vehicles=vehicles,
        background_arrivals=arrivals,
        service_durations=durations,
        port_events=port_events,
        scenario=config.scenario,
        seed=config.seed,
    )
