"""Station-status history (Parquet) and inference windows from simulator output.

The column set matches the canonical ``station_status`` schema in
``docs/DATA_CONTRACT.md``: unique by ``(scenario, station_id, ts)``,
timestamps at ``+07:00`` on five-minute boundaries.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from app.backend.contracts.enums import Scenario
from app.backend.contracts.recommendation import StatusWindow
from app.backend.contracts.simulation import FixtureBundle, ScenarioConfig
from app.backend.contracts.stations import Station, StationStatus
from app.backend.modules.simulation.domain import StepSnapshot
from app.backend.modules.simulation.engine import SimulationEngine

STATUS_COLUMNS = ["station_id", "ts", "ports_free", "ports_busy", "ports_broken", "scenario"]
KEY_COLUMNS = ["scenario", "station_id", "ts"]
_OFFSET = timedelta(hours=7)


def snapshots_to_frame(snapshots: Sequence[StepSnapshot]) -> pd.DataFrame:
    rows = [
        {
            "station_id": item.station_id,
            "ts": snapshot.ts,
            "ports_free": item.ports_free,
            "ports_busy": item.ports_busy,
            "ports_broken": item.ports_broken,
            "scenario": snapshot.scenario.value,
        }
        for snapshot in snapshots
        for item in snapshot.stations
    ]
    frame = pd.DataFrame(rows, columns=STATUS_COLUMNS)
    frame["ts"] = pd.to_datetime(frame["ts"])
    return frame.sort_values(KEY_COLUMNS, kind="mergesort").reset_index(drop=True)


def generate_status_history(
    bundle: FixtureBundle, stations: Sequence[Station], config: ScenarioConfig
) -> pd.DataFrame:
    """Replay the bundle's background load and port faults over ``config``'s window."""
    if bundle.scenario != config.scenario or bundle.seed != config.seed:
        raise ValueError("bundle and config must share scenario and seed")
    engine = SimulationEngine(
        stations,
        bundle.scenario,
        bundle.background_arrivals,
        bundle.service_durations,
        bundle.port_events,
    )
    return snapshots_to_frame(engine.run(config))


def _validate_status_frame(frame: pd.DataFrame) -> None:
    if list(frame.columns) != STATUS_COLUMNS:
        raise ValueError(f"station_status columns must be exactly {STATUS_COLUMNS}")
    if frame.empty:
        raise ValueError("station_status is empty")
    if frame.duplicated(subset=KEY_COLUMNS).any():
        raise ValueError("station_status keys (scenario, station_id, ts) must be unique")
    if (frame[["ports_free", "ports_busy", "ports_broken"]] < 0).any().any():
        raise ValueError("port counts must be non-negative")
    if not set(frame["scenario"]) <= {item.value for item in Scenario}:
        raise ValueError("unknown scenario value")
    ts = frame["ts"]
    if ts.dt.tz is None or set(ts.map(lambda item: item.utcoffset())) != {_OFFSET}:
        raise ValueError("ts must carry the +07:00 offset")
    if (ts.dt.minute % 5).any() or ts.dt.second.any():
        raise ValueError("ts must align to five-minute boundaries")


def write_status_history(frame: pd.DataFrame, path: Path) -> Path:
    _validate_status_frame(frame)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.sort_values(KEY_COLUMNS, kind="mergesort").to_parquet(path, index=False)
    return path


def build_status_window(
    frame: pd.DataFrame,
    station_id: str,
    observed_at: datetime,
    lag_minutes: tuple[int, ...] = (15, 30, 60),
    scenario: Scenario | None = None,
) -> StatusWindow:
    """Statuses at ``observed_at - lag`` for each lag; never later than ``observed_at``."""
    if any(lag < 0 for lag in lag_minutes):
        raise ValueError("lags must be non-negative")
    rows = frame.loc[frame["station_id"] == station_id]
    if scenario is None:
        names = rows["scenario"].unique()
        if len(names) != 1:
            raise ValueError("scenario is required when history holds several scenarios")
        scenario = Scenario(names[0])
    rows = rows.loc[rows["scenario"] == scenario.value].set_index("ts")
    statuses = []
    for lag in lag_minutes:
        ts = observed_at - timedelta(minutes=lag)
        if ts not in rows.index:
            raise ValueError(f"no status for {station_id} at {ts.isoformat()}")
        row = rows.loc[ts]
        free, busy, broken = (int(row[c]) for c in ("ports_free", "ports_busy", "ports_broken"))
        statuses.append(
            StationStatus(
                station_id=station_id,
                ts=ts,
                ports_free=free,
                ports_busy=busy,
                ports_broken=broken,
                n_ports=free + busy + broken,
                scenario=scenario,
            )
        )
    return StatusWindow(
        station_id=station_id,
        observed_at=observed_at,
        lags=lag_minutes,
        statuses=tuple(statuses),
    )
