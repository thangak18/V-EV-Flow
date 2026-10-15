"""Real tiny simulated model -> HTTP wiring, never a committed model binary."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.backend.api.dependencies import StartupConfigurationError, build_container
from app.backend.api.main import create_app
from app.backend.api.runtime import BackgroundStatusRepository, RuntimePredictor
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import DataSourceUnavailableError, ModelNotReadyError
from app.backend.contracts.prediction import PredictRequest
from app.backend.core.settings import Settings
from app.backend.infrastructure.repositories.files import FileStationRepository
from app.backend.modules.prediction.artifacts import save_pipeline
from app.backend.modules.prediction.labels import build_labels
from app.backend.modules.prediction.public import load_predictor
from app.backend.modules.prediction.split import temporal_split
from app.backend.modules.prediction.training import TrainingConfig, train_candidate
from app.backend.modules.simulation.public import generate_status_history
from app.backend.modules.station_data.public import (
    generate_fixture_bundle,
    load_scenario_specs,
    load_stations,
)


@pytest.fixture(scope="module")
def runtime_files(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("runtime")
    generated = root / "generated"
    generated.mkdir()
    stations = load_stations()[:2]
    (generated / "stations.json").write_text(
        json.dumps([s.model_dump(mode="json") for s in stations])
    )
    specs = load_scenario_specs()
    frames = []
    configs = {}
    for scenario in Scenario:
        spec = specs[scenario].history_spec(2, datetime.fromisoformat("2026-10-13T23:55:00+07:00"))
        bundle = generate_fixture_bundle(spec, stations, 12)
        frames.append(generate_status_history(bundle, stations, spec.to_config()))
        configs[scenario.value] = {"config": spec.to_config().model_dump(mode="json")}
    frame = pd.concat(frames, ignore_index=True)
    frame.to_parquet(generated / "station_status.parquet", index=False)
    (generated / "manifest.json").write_text(
        json.dumps({"data_type": "simulated", "scenarios": configs})
    )
    split = temporal_split(
        build_labels(frame, [15, 30, 60]),
        train_end="2026-10-12T10:00:00+07:00",
        calibration_end="2026-10-12T20:00:00+07:00",
        max_horizon_minutes=60,
    )
    trained = train_candidate(
        split,
        TrainingConfig(
            n_estimators=8,
            min_child_samples=3,
            source="stateful-runtime-test",
            data_type="simulated",
        ),
        status_frame=frame,
        stations=stations,
        seed=42,
    )
    manifest = save_pipeline(trained, root / "model", data_version="simulated-runtime-test")
    return root, manifest, frame


def settings_for(root: Path, **kwargs) -> Settings:
    return Settings(
        data_backend="file",
        data_dir=root,
        predictor_backend="model",
        model_dir=root / "model",
        **kwargs,
    )


def prediction(scenario: str = "normal", horizon: int = 30) -> dict:
    observed = pd.Timestamp("2026-10-13T16:00:00+07:00")
    return {
        "station_id": "S001",
        "scenario": scenario,
        "connector_type": "CCS2",
        "observed_at": observed.isoformat(),
        "eta": (observed + timedelta(minutes=horizon)).isoformat(),
    }


def test_real_model_http_matches_public_predictor_and_errors(runtime_files) -> None:
    root, manifest, _ = runtime_files
    app = create_app(settings_for(root, fake_prediction_horizon_minutes=120))
    with TestClient(app) as client:
        for scenario in Scenario:
            for horizon in (15, 30, 60):
                payload = prediction(scenario.value, horizon)
                response = client.post("/api/predict", json=payload)
                assert response.status_code == 200, response.text
                result = response.json()
                assert result["model_version"] == manifest.model_version
                assert result["data_type"] == "simulated"
                direct = load_predictor(
                    root / "model",
                    app.state.container.status_repositories_by_scenario[scenario],
                    app.state.container.stations,
                    status_data_type=DataType.SIMULATED,
                )
                assert result == direct.predict(PredictRequest.model_validate(payload)).model_dump(
                    mode="json"
                )
        assert client.post("/api/predict", json=prediction(horizon=65)).status_code == 422
        assert (
            client.post("/api/predict", json=prediction() | {"station_id": "missing"}).status_code
            == 404
        )
        missing = prediction() | {
            "observed_at": "2026-10-14T16:00:00+07:00",
            "eta": "2026-10-14T16:30:00+07:00",
        }
        response = client.post("/api/predict", json=missing)
        assert response.status_code == 503
        assert response.json()["code"] == "DATA_SOURCE_UNAVAILABLE"
        request = {
            "request_id": "runtime-driver",
            "origin": {"lat": 10.78, "lng": 106.7},
            "destination": {"lat": 10.35, "lng": 107.08},
            "observed_at": prediction()["observed_at"],
            "depart_time": prediction()["observed_at"],
            "scenario": "normal",
            "vehicle": {
                "soc_pct": 20,
                "battery_kwh": 60,
                "consumption_kwh_per_km": 0.18,
                "connector_type": "CCS2",
            },
        }
        first = client.post("/api/recommend", json=request)
        assert first.status_code == 200, first.text
        assert first.json()["primary"] is not None
        assert first.json()["model_version"] == manifest.model_version
        assert first.json()["data_type"] == "simulated"
        assert client.post("/api/recommend", json=request).json() == first.json()
        assert client.post("/api/reset", json={}).status_code == 200


def test_stateful_three_strategies_isolated_reproducible_and_versioned(runtime_files) -> None:
    root, manifest, _ = runtime_files
    app = create_app(settings_for(root, simulation_backend="stateful"))
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/simulate",
                json={"scenario": "normal", "strategy": "nearest", "seed": -1, "vehicle_count": 12},
            ).status_code
            == 422
        )
        results = []
        for strategy in ("nearest", "currently_available", "ai_allocation"):
            request = {"scenario": "normal", "strategy": strategy, "seed": 42, "vehicle_count": 12}
            response = client.post("/api/simulate", json=request)
            assert response.status_code == 200, response.text
            result = response.json()
            results.append(result)
            assert result["metrics"]["vehicle_count"] == 12
            assert result["model_version"] == (
                manifest.model_version if strategy == "ai_allocation" else "simulated-baseline-v1"
            )
        assert len({r["fixture_hash"] for r in results}) == 1
        repeated = client.post(
            "/api/simulate",
            json={
                "scenario": "normal",
                "strategy": "ai_allocation",
                "seed": 42,
                "vehicle_count": 12,
            },
        )
        assert repeated.json() == results[-1]
        other = client.post(
            "/api/simulate",
            json={"scenario": "normal", "strategy": "nearest", "seed": 43, "vehicle_count": 12},
        )
        assert other.json()["fixture_hash"] != results[0]["fixture_hash"]
        observed = pd.Timestamp(prediction()["observed_at"]).to_pydatetime()
        assert (
            asyncio.run(app.state.container.virtual_load_store.snapshot(observed, Scenario.NORMAL))
            == {}
        )


def test_background_history_omits_only_missing_past_and_requires_current(runtime_files) -> None:
    root, _, frame = runtime_files
    stations = FileStationRepository(root / "generated/stations.json")
    rows = frame.loc[frame.scenario == "normal"]
    repo = BackgroundStatusRepository(rows, stations, Scenario.NORMAL)
    start = rows.ts.min().to_pydatetime()
    assert len(repo.window("S001", start, (0, 15, 30, 60)).statuses) == 1
    for lags in ((-5,), (65,), (True,), ()):
        with pytest.raises(ValueError):
            repo.window("S001", start, lags)
    with pytest.raises(ValueError):
        repo.window("S001", start + timedelta(seconds=1), (0,))
    with pytest.raises(DataSourceUnavailableError):
        repo.window("S001", start - timedelta(minutes=5), (0,))


def test_invalid_model_never_silently_falls_back(runtime_files, tmp_path: Path) -> None:
    root, _, _ = runtime_files
    with pytest.raises(StartupConfigurationError, match="model artifact"):
        build_container(settings_for(root).model_copy(update={"model_dir": tmp_path}))


def test_inference_failure_is_typed_instead_of_fake_success() -> None:
    class Broken:
        def predict(self, request: PredictRequest):
            raise ValueError("invalid feature order")

    with pytest.raises(ModelNotReadyError):
        RuntimePredictor(Broken()).predict(PredictRequest.model_validate(prediction()))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"predictor_backend": "model", "data_backend": "mock"},
        {"simulation_backend": "stateful", "predictor_backend": "fake"},
    ],
)
def test_invalid_runtime_combinations_fail_settings(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        Settings(**kwargs)
