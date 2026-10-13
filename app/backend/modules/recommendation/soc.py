"""Pure feasibility before prediction, using km, kWh, and SOC percentage points.

The shared FeasibleCandidate requires p_available and therefore belongs after
prediction. These internal results retain the upstream candidate and SOC only;
C5 can combine them with a real prediction to construct the shared DTO.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite

from app.backend.contracts.recommendation import RouteResult, Vehicle
from app.backend.contracts.stations import Station, StationStatus


@dataclass(frozen=True)
class RouteCandidate:
    """One upstream-selected route and caller-supplied current status.

    ETA and nonnegative detour are supplied upstream, not inferred here.
    Frozen wrappers do not make the referenced shared Pydantic DTOs immutable.
    """

    station: Station
    status: StationStatus
    route: RouteResult
    eta: datetime
    detour_km: float


@dataclass(frozen=True)
class FeasibleRouteCandidate:
    candidate: RouteCandidate
    arrival_soc_pct: float


class RejectionReason(StrEnum):
    CONNECTOR_INCOMPATIBLE = "connector_incompatible"
    CONNECTOR_CAPACITY_UNKNOWN = "connector_capacity_unknown"
    NO_WORKING_PORTS = "no_working_ports"
    INSUFFICIENT_ARRIVAL_SOC = "insufficient_arrival_soc"


@dataclass(frozen=True)
class RejectedCandidate:
    candidate: RouteCandidate
    reason: RejectionReason


@dataclass(frozen=True)
class FeasibilityResult:
    accepted: tuple[FeasibleRouteCandidate, ...]
    rejected: tuple[RejectedCandidate, ...]


def _nonnegative_finite(value: float, name: str) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")


def _validate_vehicle(vehicle: Vehicle) -> None:
    for name in ("battery_kwh", "consumption_kwh_per_km"):
        value = getattr(vehicle, name)
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")


def arrival_soc_pct(vehicle: Vehicle, distance_km: float) -> float:
    """Calculate unrounded arrival SOC; negative results remain negative."""
    _validate_vehicle(vehicle)
    _nonnegative_finite(distance_km, "distance_km")
    arrival = (
        vehicle.soc_pct - 100 * distance_km * vehicle.consumption_kwh_per_km / vehicle.battery_kwh
    )
    if not isfinite(arrival):
        raise ValueError("calculated arrival SOC must be finite")
    return arrival


def connector_compatible(vehicle: Vehicle, station: Station) -> bool:
    """Exact connector membership only; this does not prove working capacity."""
    return vehicle.connector_type in station.connector_types


def working_ports(station: Station, status: StationStatus) -> int:
    """Count operational ports, including busy ports, after consistency checks."""
    if not isinstance(status, StationStatus):
        raise ValueError("status must be a current StationStatus")
    if station.station_id != status.station_id:
        raise ValueError("station_id must match between station and status")
    if station.n_ports != status.n_ports:
        raise ValueError("n_ports must match between station and status")
    return station.n_ports - status.ports_broken


def evaluate_feasibility(
    vehicle: Vehicle, candidates: Iterable[RouteCandidate], min_soc_pct: float
) -> FeasibilityResult:
    """Preserve input order and record the first business rejection per route.

    Invalid inputs raise ValueError, even for incompatible stations. Business
    priority is connector mismatch, unknown connector capacity, no working
    ports, then insufficient SOC. Current status selection is the caller's
    responsibility; no future availability is inferred from free/busy counts.
    """
    if not isfinite(min_soc_pct) or not 0 <= min_soc_pct <= 100:
        raise ValueError("min_soc_pct must be finite and between 0 and 100")
    _validate_vehicle(vehicle)
    accepted: list[FeasibleRouteCandidate] = []
    rejected: list[RejectedCandidate] = []
    for candidate in candidates:
        if not isinstance(candidate.station, Station):
            raise ValueError("station must be a Station")
        capacity = working_ports(candidate.station, candidate.status)
        if not isinstance(candidate.route, RouteResult):
            raise ValueError("route must be a RouteResult")
        _nonnegative_finite(candidate.route.distance_km, "distance_km")
        _nonnegative_finite(candidate.route.duration_minutes, "duration_minutes")
        _nonnegative_finite(candidate.detour_km, "detour_km")
        if (
            not isinstance(candidate.eta, datetime)
            or candidate.eta.tzinfo is None
            or candidate.eta.utcoffset() is None
        ):
            raise ValueError("eta must be timezone-aware")

        reason: RejectionReason | None = None
        if not connector_compatible(vehicle, candidate.station):
            reason = RejectionReason.CONNECTOR_INCOMPATIBLE
        elif len(set(candidate.station.connector_types)) != 1:
            reason = RejectionReason.CONNECTOR_CAPACITY_UNKNOWN
        elif capacity == 0:
            reason = RejectionReason.NO_WORKING_PORTS
        else:
            arrival = arrival_soc_pct(vehicle, candidate.route.distance_km)
            if arrival < min_soc_pct:
                reason = RejectionReason.INSUFFICIENT_ARRIVAL_SOC
            else:
                accepted.append(FeasibleRouteCandidate(candidate, arrival))
        if reason is not None:
            rejected.append(RejectedCandidate(candidate, reason))
    return FeasibilityResult(tuple(accepted), tuple(rejected))


def filter_feasible(
    vehicle: Vehicle, candidates: Iterable[RouteCandidate], min_soc_pct: float
) -> tuple[FeasibleRouteCandidate, ...]:
    """Return pre-prediction candidates only; no probability, ranking or routing."""
    return evaluate_feasibility(vehicle, candidates, min_soc_pct).accepted
