import json
from datetime import datetime, timedelta
from pathlib import Path

from app.backend.contracts.enums import Scenario
from app.backend.contracts.recommendation import StatusWindow
from app.backend.contracts.stations import Station, StationStatus

_FIXTURE = (
    Path(__file__).resolve().parents[2] / "modules" / "station_data" / "fixtures" / "stations.json"
)


class MockStationRepository:
    def __init__(self, fixture_path: Path | None = None) -> None:
        path = fixture_path or _FIXTURE
        self._stations = tuple(
            Station.model_validate(item) for item in json.loads(path.read_text())
        )
        self._by_id = {station.station_id: station for station in self._stations}

    def list_stations(self) -> tuple[Station, ...]:
        return self._stations

    def get_station(self, station_id: str) -> Station:
        try:
            return self._by_id[station_id]
        except KeyError as exc:
            raise KeyError(f"unknown station: {station_id}") from exc


class MockStatusRepository:
    def __init__(self, station_repository: MockStationRepository | None = None) -> None:
        self._stations = station_repository or MockStationRepository()

    def window(
        self, station_id: str, observed_at: datetime, lags: tuple[int, ...] = (15, 30, 60)
    ) -> StatusWindow:
        station = self._stations.get_station(station_id)
        statuses = tuple(
            StationStatus(
                station_id=station_id,
                ts=observed_at - timedelta(minutes=lag),
                ports_free=station.n_ports,
                ports_busy=0,
                ports_broken=0,
                n_ports=station.n_ports,
                scenario=Scenario.NORMAL,
            )
            for lag in lags
        )
        return StatusWindow(
            station_id=station_id, observed_at=observed_at, lags=lags, statuses=statuses
        )
