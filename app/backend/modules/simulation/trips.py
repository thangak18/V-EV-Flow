"""Foreground vehicle trips derived from a fixture bundle.

``Vehicle`` in the shared contract has no identity, position or departure time,
so the simulation derives them here from ``bundle.seed``. The result is a pure
function of the bundle and window: every strategy replays identical trips.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from app.backend.contracts.common import Coordinate
from app.backend.contracts.recommendation import Vehicle
from app.backend.contracts.simulation import FixtureBundle, ScenarioConfig

# Corridor ends (assumed cluster centres) and spread in degrees.
HCM = Coordinate(lat=10.78, lng=106.70)
VUNG_TAU = Coordinate(lat=10.38, lng=107.08)
_SPREAD_DEG = {"hcm": 0.04, "vung_tau": 0.03}
ARRIVAL_MARGIN = timedelta(hours=4)  # departures stop this long before the window end
_SALT = 7919  # keeps the trip stream separate from the fixture generator stream


@dataclass(frozen=True)
class VehicleTrip:
    vehicle_id: str
    vehicle: Vehicle
    origin: Coordinate
    destination: Coordinate
    depart_at: datetime
    complies: bool


def _point(rng: np.random.Generator, centre: Coordinate, spread: float) -> Coordinate:
    lat = float(np.clip(centre.lat + rng.normal(0, spread), -90, 90))
    lng = float(np.clip(centre.lng + rng.normal(0, spread), -180, 180))
    return Coordinate(lat=round(lat, 5), lng=round(lng, 5))


def build_trips(
    bundle: FixtureBundle, config: ScenarioConfig, vehicle_count: int
) -> tuple[VehicleTrip, ...]:
    """First ``vehicle_count`` vehicles with deterministic origin, destination and departure."""
    if vehicle_count > len(bundle.vehicles):
        raise ValueError(f"bundle holds {len(bundle.vehicles)} vehicles, {vehicle_count} requested")
    step = timedelta(minutes=config.step_minutes)
    window_start = max(config.start, config.end - timedelta(hours=24) + step)
    depart_steps = int((config.end - ARRIVAL_MARGIN - window_start) / step) + 1
    if depart_steps < 1:
        raise ValueError("scenario window is too short for vehicle departures")
    rng = np.random.default_rng([bundle.seed, _SALT])
    outbound = rng.random(vehicle_count) < 0.7
    departures = rng.integers(0, depart_steps, size=vehicle_count)
    complies = rng.random(vehicle_count) < config.compliance_rate
    trips = []
    for index in range(vehicle_count):
        near, far = (HCM, VUNG_TAU) if outbound[index] else (VUNG_TAU, HCM)
        near_key, far_key = ("hcm", "vung_tau") if outbound[index] else ("vung_tau", "hcm")
        trips.append(
            VehicleTrip(
                vehicle_id=f"V{index + 1:03d}",
                vehicle=bundle.vehicles[index],
                origin=_point(rng, near, _SPREAD_DEG[near_key]),
                destination=_point(rng, far, _SPREAD_DEG[far_key]),
                depart_at=window_start + int(departures[index]) * step,
                complies=bool(complies[index]),
            )
        )
    return tuple(sorted(trips, key=lambda trip: (trip.depart_at, trip.vehicle_id)))
