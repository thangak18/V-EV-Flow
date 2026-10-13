from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.backend.contracts.enums import Scenario
from app.backend.contracts.simulation import (
    BackgroundArrival,
    FixtureBundle,
    PortEvent,
    ScenarioConfig,
)
from app.backend.contracts.stations import Station
from app.backend.modules.simulation.history import (
    STATUS_COLUMNS,
    build_status_window,
    generate_status_history,
    write_status_history,
)

T0 = datetime(2026, 10, 12, 0, 0, tzinfo=timezone(timedelta(hours=7)))
STEP = timedelta(minutes=5)
STEPS = 2 * 288


def make_stations() -> tuple[Station, ...]:
    return tuple(
        Station(
            station_id=f"S{index:03d}",
            name="Test",
            lat=10.0,
            lng=106.0,
            n_ports=ports,
            power_kw=60.0,
            connector_types=["CCS2"],
            network="test",
            station_type="urban",
            source="test",
            assumptions=["test"],
        )
        for index, ports in ((1, 4), (2, 6))
    )


def make_config(seed: int = 1) -> ScenarioConfig:
    return ScenarioConfig(
        scenario=Scenario.NORMAL,
        seed=seed,
        start=T0,
        end=T0 + (STEPS - 1) * STEP,
        step_minutes=5,
        demand_multiplier=1.0,
        compliance_rate=0.7,
    )


def make_bundle(seed: int = 1) -> FixtureBundle:
    rng = np.random.default_rng(seed)
    stations = make_stations()
    arrivals = tuple(
        BackgroundArrival(
            station_id=stations[int(rng.integers(0, 2))].station_id,
            ts=T0 + int(step) * STEP,
            vehicle_id=f"B{index:04d}",
        )
        for index, step in enumerate(np.sort(rng.integers(0, STEPS, size=400)))
    )
    events = tuple(
        PortEvent(station_id="S001", ts=T0 + step * STEP, ports_delta=delta)
        for step, delta in ((100, -1), (130, 1), (300, -1), (320, 1))
    )
    return FixtureBundle(
        vehicles=(),
        background_arrivals=arrivals,
        service_durations=tuple(float(item) for item in rng.uniform(20, 45, size=400)),
        port_events=events,
        scenario=Scenario.NORMAL,
        seed=seed,
    )


@pytest.fixture(scope="module")
def history() -> pd.DataFrame:
    return generate_status_history(make_bundle(), make_stations(), make_config())


def test_history_has_exact_columns_unique_keys_and_offset(history: pd.DataFrame) -> None:
    assert list(history.columns) == STATUS_COLUMNS
    assert len(history) == STEPS * 2
    assert not history.duplicated(subset=["scenario", "station_id", "ts"]).any()
    assert {ts.utcoffset() for ts in history["ts"]} == {timedelta(hours=7)}
    assert set(history["scenario"]) == {"normal"}


def test_history_conserves_ports_per_station(history: pd.DataFrame) -> None:
    capacity = {s.station_id: s.n_ports for s in make_stations()}
    total = history[["ports_free", "ports_busy", "ports_broken"]].sum(axis=1)
    assert (total == [capacity[item] for item in history["station_id"]]).all()


def test_history_is_reproducible(history: pd.DataFrame) -> None:
    again = generate_status_history(make_bundle(), make_stations(), make_config())
    pd.testing.assert_frame_equal(history, again)


def test_history_rejects_mismatched_bundle_and_config() -> None:
    with pytest.raises(ValueError, match="share scenario and seed"):
        generate_status_history(make_bundle(1), make_stations(), make_config(2))


def test_write_status_history_round_trips_parquet(history: pd.DataFrame, tmp_path: Path) -> None:
    path = write_status_history(history, tmp_path / "out" / "station_status.parquet")
    loaded = pd.read_parquet(path)
    assert list(loaded.columns) == STATUS_COLUMNS
    assert len(loaded) == len(history)
    assert {ts.utcoffset() for ts in loaded["ts"]} == {timedelta(hours=7)}


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda f: f.drop(columns=["scenario"]), "columns"),
        (lambda f: f.iloc[0:0], "empty"),
        (lambda f: pd.concat([f, f.iloc[:1]]), "unique"),
        (lambda f: f.assign(ports_free=-1), "non-negative"),
        (lambda f: f.assign(scenario="bogus"), "scenario"),
        (lambda f: f.assign(ts=f["ts"].dt.tz_localize(None)), "offset"),
        (lambda f: f.assign(ts=f["ts"] + pd.Timedelta(minutes=1)), "five-minute"),
    ],
)
def test_write_status_history_rejects_invalid_frames(
    history: pd.DataFrame,
    tmp_path: Path,
    mutate,
    message: str,  # noqa: ANN001
) -> None:
    with pytest.raises(ValueError, match=message):
        write_status_history(mutate(history), tmp_path / "bad.parquet")


def test_status_window_never_contains_future_timestamps(history: pd.DataFrame) -> None:
    observed = history["ts"].iloc[-1]
    window = build_status_window(history, "S001", observed)
    assert window.lags == (15, 30, 60)
    assert all(item.ts <= observed for item in window.statuses)
    assert [observed - item.ts for item in window.statuses] == [
        timedelta(minutes=m) for m in (15, 30, 60)
    ]
    assert all(item.scenario is Scenario.NORMAL for item in window.statuses)


def test_status_window_errors(history: pd.DataFrame) -> None:
    observed = history["ts"].iloc[-1]
    with pytest.raises(ValueError, match="non-negative"):
        build_status_window(history, "S001", observed, (-5,))
    with pytest.raises(ValueError, match="no status"):
        build_status_window(history, "S001", history["ts"].iloc[0], (15,))
    multi = pd.concat([history, history.assign(scenario="tet")])
    with pytest.raises(ValueError, match="scenario is required"):
        build_status_window(multi, "S001", observed)
    assert build_status_window(multi, "S001", observed, scenario=Scenario.TET).statuses


def test_model_snapshot_has_current_and_exact_lags_without_future_rows(
    history: pd.DataFrame,
) -> None:
    observed = history["ts"].iloc[-1] - timedelta(minutes=30)
    window = build_status_window(history, "S002", observed, (0, 15, 30, 60))
    assert window.lags == (0, 15, 30, 60)
    assert [observed - item.ts for item in window.statuses] == [
        timedelta(minutes=m) for m in (0, 15, 30, 60)
    ]
    assert window.statuses[0].ts == observed
    assert all(item.ts <= observed for item in window.statuses)
    assert all(item.station_id == "S002" for item in window.statuses)


def test_model_snapshot_is_scenario_specific(history: pd.DataFrame) -> None:
    observed = history["ts"].iloc[-1]
    tet = history.assign(scenario="tet", ports_free=0, ports_busy=4, ports_broken=2)
    both = pd.concat([history, tet])
    normal = build_status_window(both, "S002", observed, (0, 15), scenario=Scenario.NORMAL)
    crowded = build_status_window(both, "S002", observed, (0, 15), scenario=Scenario.TET)
    assert {item.scenario for item in normal.statuses} == {Scenario.NORMAL}
    assert {item.scenario for item in crowded.statuses} == {Scenario.TET}
    assert all(item.ports_free == 0 for item in crowded.statuses)
