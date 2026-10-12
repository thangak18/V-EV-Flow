"""Records and mutable runtime state for the five-minute charging simulator."""

from dataclasses import dataclass, field
from datetime import datetime

from app.backend.contracts.enums import Scenario


@dataclass(frozen=True)
class ChargingSession:
    vehicle_id: str
    started_at: datetime
    ends_at: datetime
    service_minutes: float


@dataclass(frozen=True)
class QueuedVehicle:
    vehicle_id: str
    service_minutes: float


@dataclass(frozen=True)
class StationSnapshot:
    station_id: str
    ports_free: int
    ports_busy: int
    ports_broken: int
    n_ports: int
    queue_length: int
    active_vehicle_ids: frozenset[str]


@dataclass(frozen=True)
class StepSnapshot:
    ts: datetime
    scenario: Scenario
    stations: tuple[StationSnapshot, ...]

    def station(self, station_id: str) -> StationSnapshot:
        for item in self.stations:
            if item.station_id == station_id:
                return item
        raise KeyError(station_id)

    @property
    def active_vehicle_ids(self) -> frozenset[str]:
        return frozenset().union(*(item.active_vehicle_ids for item in self.stations))


@dataclass
class StationRuntimeState:
    station_id: str
    n_ports: int
    broken: int = 0
    sessions: list[ChargingSession] = field(default_factory=list)
    queue: list[QueuedVehicle] = field(default_factory=list)

    @property
    def busy(self) -> int:
        return len(self.sessions)

    @property
    def free(self) -> int:
        return self.n_ports - self.broken - self.busy
