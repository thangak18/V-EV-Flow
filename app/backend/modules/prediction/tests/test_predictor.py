"""Runtime predictor conformance, no-future access and strict input validation."""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.ports import Predictor
from app.backend.contracts.prediction import PredictRequest
from app.backend.contracts.recommendation import StatusWindow
from app.backend.contracts.stations import Station, StationStatus
from app.backend.modules.prediction.artifacts import save_pipeline
from app.backend.modules.prediction.features import FEATURE_COLUMNS
from app.backend.modules.prediction.labels import LABEL_COLUMNS, build_labels
from app.backend.modules.prediction.predictor import ModelPredictor
from app.backend.modules.prediction.public import load_predictor
from app.backend.modules.prediction.split import temporal_split
from app.backend.modules.prediction.training import TrainingConfig, train_candidate


class Stations:
    def __init__(self, stations: tuple[Station, ...]) -> None:
        self.by_id = {station.station_id: station for station in stations}

    def list_stations(self) -> tuple[Station, ...]:
        return tuple(self.by_id.values())

    def get_station(self, station_id: str) -> Station:
        return self.by_id[station_id]


class Windows:
    def __init__(self, frame: pd.DataFrame, stations: Stations) -> None:
        self.frame = frame
        self.stations = stations
        self.calls: list[tuple[str, datetime, tuple[int, ...]]] = []
        self.omit: set[int] = set()
        self.inject_future = False

    def window(
        self, station_id: str, observed_at: datetime, lags: tuple[int, ...] = (15, 30, 60)
    ) -> StatusWindow:
        self.calls.append((station_id, observed_at, lags))
        rows = self.frame.loc[
            (self.frame["station_id"] == station_id)
            & self.frame["ts"].isin(
                [
                    pd.Timestamp(observed_at) - pd.Timedelta(minutes=lag)
                    for lag in lags
                    if lag not in self.omit
                ]
            )
            & (self.frame["scenario"] == "normal")
        ]
        station = self.stations.get_station(station_id)
        statuses = [
            StationStatus(
                station_id=station_id,
                ts=row.ts,
                ports_free=int(row.ports_free),
                ports_busy=int(row.ports_busy),
                ports_broken=int(row.ports_broken),
                n_ports=station.n_ports,
                scenario=Scenario.NORMAL,
            )
            for row in rows.itertuples()
        ]
        if self.inject_future:
            statuses.append(
                StationStatus(
                    station_id=station_id,
                    ts=observed_at + timedelta(minutes=5),
                    ports_free=station.n_ports,
                    ports_busy=0,
                    ports_broken=0,
                    n_ports=station.n_ports,
                    scenario=Scenario.NORMAL,
                )
            )
        return StatusWindow(
            station_id=station_id,
            observed_at=observed_at,
            lags=lags,
            statuses=tuple(statuses),
        )


@pytest.fixture(scope="module")
def training_bundle(tmp_path_factory: pytest.TempPathFactory):
    stations = tuple(
        Station(
            station_id=f"S00{index}",
            name=f"Fixture {index}",
            lat=10.0,
            lng=107.0,
            n_ports=4,
            power_kw=120.0,
            connector_types=["CCS2"],
            network="synthetic",
            station_type="highway",
            source="synthetic",
            assumptions=["uniform connector"],
        )
        for index in (1, 2)
    )
    rng = np.random.default_rng(33)
    start = pd.Timestamp("2026-10-12T00:00:00+07:00")
    records: list[dict[str, object]] = []
    for scenario in ("normal", "tet"):
        for station in stations:
            for tick in range(400):
                free = int(rng.binomial(4, 0.62 if scenario == "normal" else 0.38))
                records.append(
                    {
                        "station_id": station.station_id,
                        "scenario": scenario,
                        "ts": start + pd.Timedelta(minutes=5 * tick),
                        "ports_free": free,
                        "ports_busy": 4 - free,
                        "ports_broken": 0,
                    }
                )
    from app.backend.modules.prediction.dataset import validate_status_frame

    status = validate_status_frame(pd.DataFrame(records), stations)
    split = temporal_split(
        build_labels(status, [15, 30]),
        train_end="2026-10-12T09:00:00+07:00",
        calibration_end="2026-10-12T19:00:00+07:00",
        max_horizon_minutes=30,
    )
    pipeline = train_candidate(
        split,
        TrainingConfig(n_estimators=12, min_child_samples=4, source="synthetic-test"),
        status_frame=status,
        stations=stations,
        seed=33,
    )
    directory = tmp_path_factory.mktemp("trained-predictor")
    manifest = save_pipeline(pipeline, directory, data_version="simulated-fixture")
    return stations, status, pipeline, directory, manifest


@pytest.fixture
def runtime(training_bundle):  # noqa: ANN201
    stations, status, pipeline, directory, manifest = training_bundle
    repository = Stations(stations)
    windows = Windows(status, repository)
    predictor = load_predictor(directory, windows, repository, status_data_type=DataType.SIMULATED)
    return predictor, windows, repository, pipeline, manifest


@pytest.fixture
def sample_request() -> PredictRequest:
    observed = datetime.fromisoformat("2026-10-13T00:00:00+07:00")
    return PredictRequest(
        station_id="S001",
        observed_at=observed,
        eta=observed + timedelta(minutes=30),
        connector_type="CCS2",
        scenario=Scenario.NORMAL,
    )


def test_port_roundtrip_matches_training_features(runtime, sample_request, training_bundle) -> None:  # noqa: ANN001
    predictor, windows, _repository, pipeline, manifest = runtime
    _stations, status, *_ = training_bundle
    assert isinstance(predictor, Predictor)
    result = predictor.predict(sample_request)
    assert windows.calls == [("S001", sample_request.observed_at, (0, 15, 30, 60))]
    label = pd.DataFrame(
        [
            {
                "station_id": sample_request.station_id,
                "scenario": "normal",
                "observed_at": sample_request.observed_at,
                "eta": sample_request.eta,
                "horizon_minutes": 30,
                "target_available": 0,
            }
        ],
        columns=list(LABEL_COLUMNS),
    )
    features = pipeline.feature_builder.build(status, label).X
    assert tuple(features.columns) == FEATURE_COLUMNS
    assert result.p_available == pytest.approx(float(pipeline.predict_proba(features)[0, 1]))
    assert result.model_version == manifest.model_version
    assert result.contract_version == manifest.contract_version
    assert result.explanation_method == "rule"
    assert result.data_type == DataType.SIMULATED
    assert result.reasons


@pytest.mark.parametrize("minutes", [0, 1, 31, 35, 90])
def test_rejects_unsupported_horizon_before_reading_status(
    runtime, sample_request, minutes: int
) -> None:  # noqa: ANN001
    predictor, windows, *_ = runtime
    with pytest.raises(ValueError, match="horizon|ETA|five"):
        predictor.predict(
            sample_request.model_copy(
                update={"eta": sample_request.observed_at + timedelta(minutes=minutes)}
            )
        )
    assert windows.calls == []


def test_missing_current_and_missing_lags(runtime, sample_request) -> None:  # noqa: ANN001
    predictor, windows, *_ = runtime
    windows.omit = {0}
    with pytest.raises(ValueError, match="current|observed_at"):
        predictor.predict(sample_request)
    windows.omit = {15, 30, 60}
    result = predictor.predict(sample_request)
    assert 0 <= result.p_available <= 1


def test_future_snapshot_is_rejected(runtime, sample_request) -> None:  # noqa: ANN001
    predictor, windows, *_ = runtime
    windows.inject_future = True
    with pytest.raises(ValueError, match="future|observed_at"):
        predictor.predict(sample_request)


def test_connector_mismatch_and_mixed_connector_station_rejected(runtime, sample_request) -> None:  # noqa: ANN001
    predictor, windows, stations, *_ = runtime
    with pytest.raises(ValueError, match="connector"):
        predictor.predict(sample_request.model_copy(update={"connector_type": "NACS"}))
    stations.by_id["S001"] = stations.by_id["S001"].model_copy(
        update={"connector_types": ["CCS2", "CHAdeMO"]}
    )
    with pytest.raises(ValueError, match="mixed|aggregate|connector"):
        predictor.predict(sample_request)
    assert windows.calls == []


def test_station_metadata_mismatch_and_unknown_station(runtime, sample_request) -> None:  # noqa: ANN001
    predictor, _windows, stations, *_ = runtime
    with pytest.raises(KeyError, match="S099"):
        predictor.predict(sample_request.model_copy(update={"station_id": "S099"}))
    stations.by_id["S001"] = stations.by_id["S001"].model_copy(update={"power_kw": 220.0})
    with pytest.raises(ValueError, match="metadata|retrain|power"):
        predictor.predict(sample_request)


def test_rejects_scenario_and_window_mismatch(runtime, sample_request) -> None:  # noqa: ANN001
    predictor, windows, *_ = runtime
    with pytest.raises(ValueError, match="scenario|current"):
        predictor.predict(sample_request.model_copy(update={"scenario": Scenario.TET}))


def test_loader_rejects_missing_model(tmp_path: Path, runtime) -> None:  # noqa: ANN001
    _predictor, windows, stations, *_ = runtime
    with pytest.raises(FileNotFoundError):
        load_predictor(tmp_path, windows, stations)


def test_provenance_marks_mixed_sources(runtime, sample_request, training_bundle) -> None:  # noqa: ANN001
    _predictor, windows, stations, *_ = runtime
    directory = training_bundle[3]
    predictor = load_predictor(directory, windows, stations, status_data_type=DataType.MOCK)
    assert isinstance(predictor, ModelPredictor)
    assert predictor.predict(sample_request).data_type == DataType.MIXED


@pytest.mark.parametrize("scenario", list(Scenario))
@pytest.mark.parametrize("missing", [(), (15,), (15, 30, 60)])
def test_observation_features_equal_batch_builder(runtime, sample_request, scenario, missing):
    predictor, windows, stations, pipeline, _ = runtime
    windows.omit = set(missing)
    request = sample_request.model_copy(update={"scenario": scenario})
    original = windows.window(request.station_id, request.observed_at, (0, 15, 30, 60))
    window = original.model_copy(
        update={
            "statuses": tuple(
                s.model_copy(update={"scenario": scenario}) for s in original.statuses
            )
        }
    )
    current, frame = predictor._frame_from_window(window, request, stations.get_station("S001"))
    labels = pd.DataFrame(
        [
            dict(
                station_id="S001",
                scenario=scenario.value,
                observed_at=request.observed_at,
                eta=request.eta,
                horizon_minutes=30,
                target_available=0,
            )
        ]
    )
    expected = pipeline.feature_builder.build(frame, labels).X
    actual = pipeline.feature_builder.observation_features(current, window.statuses, 30)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False, atol=1e-12, rtol=0)
    np.testing.assert_allclose(
        pipeline.predict_proba(actual), pipeline.predict_proba(expected), rtol=0, atol=1e-12
    )
