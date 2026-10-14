import json
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.backend.api.main import create_app
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import ModelNotReadyError
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.core.settings import Settings
from app.backend.tests.api.test_mock_api import recommendation_payload


class RecordingPredictor:
    def __init__(self) -> None:
        self.calls: list[PredictRequest] = []

    def predict(self, request: PredictRequest) -> PredictionResult:
        self.calls.append(request)
        return PredictionResult(
            station_id=request.station_id,
            eta=request.eta,
            p_available=0.37129,
            reasons=["Controlled future prediction; not current occupancy"],
            explanation_method="rule",
            model_version="connector-regression-v1",
            data_type=DataType.SIMULATED,
        )


@pytest.fixture(params=["mock", "file"])
def prediction_app(
    request: pytest.FixtureRequest, tmp_path: Path
) -> tuple[FastAPI, RecordingPredictor]:
    fixture_path = (
        Path(__file__).resolve().parents[2] / "modules/station_data/fixtures/stations.json"
    )
    stations = json.loads(fixture_path.read_text())
    stations[0]["connector_types"] = ["CCS2", "Type2"]
    for directory in (tmp_path / "fixtures", tmp_path / "generated"):
        directory.mkdir()
        (directory / "stations.json").write_text(json.dumps(stations))
    observed_at = datetime.fromisoformat("2026-10-13T16:00:00+07:00")
    pd.DataFrame(
        [
            {
                "station_id": station["station_id"],
                "ts": observed_at,
                "ports_free": 0,
                "ports_busy": station["n_ports"],
                "ports_broken": 0,
                "scenario": scenario.value,
            }
            for station in stations
            for scenario in Scenario
        ]
    ).to_parquet(tmp_path / "generated/station_status.parquet", index=False)
    app = create_app(
        Settings(
            data_backend=request.param,
            data_dir=tmp_path,
            predictor_backend="fake",
            route_backend="fake",
            fake_prediction_horizon_minutes=60,
        )
    )
    predictor = RecordingPredictor()
    app.state.container.predictors_by_scenario[Scenario.TET] = predictor
    return app, predictor


def prediction_payload(connector: str = "CCS2") -> dict[str, str]:
    return {
        "station_id": "S001",
        "observed_at": "2026-10-13T16:00:00+07:00",
        "eta": "2026-10-13T16:30:00+07:00",
        "connector_type": connector,
        "scenario": "tet",
    }


@pytest.mark.parametrize("connector", ["CCS2", "Type2"])
async def test_predict_supported_connectors_preserve_result_and_state(
    prediction_app: tuple[FastAPI, RecordingPredictor], connector: str
) -> None:
    app, predictor = prediction_app
    container = app.state.container
    station_before = container.stations.get_station("S001").model_dump(mode="json")
    payload = prediction_payload(connector)
    eta = datetime.fromisoformat(payload["eta"])
    before = {
        scenario: await container.virtual_load_store.snapshot(eta, scenario)
        for scenario in Scenario
    }
    if container.settings.data_backend == "file":
        status = container.status_repositories_by_scenario[Scenario.TET].window(
            "S001", datetime.fromisoformat(payload["observed_at"]), lags=(0,)
        )
        assert status.statuses[0].ports_free == 0
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/predict", json=payload)
    assert response.status_code == 200
    assert len(predictor.calls) == 1
    assert predictor.calls[0].model_dump(mode="json") == payload
    assert response.json() == PredictionResult(
        station_id="S001",
        eta=eta,
        p_available=0.37129,
        reasons=["Controlled future prediction; not current occupancy"],
        explanation_method="rule",
        model_version="connector-regression-v1",
        data_type=DataType.SIMULATED,
    ).model_dump(mode="json")
    assert container.stations.get_station("S001").model_dump(mode="json") == station_before
    for scenario in Scenario:
        assert await container.virtual_load_store.snapshot(eta, scenario) == before[scenario]


@pytest.mark.parametrize("station_id, expected_status", [("S001", 422), ("UNKNOWN", 404)])
def test_predict_rejects_incompatible_or_unknown_station_before_inference(
    prediction_app: tuple[FastAPI, RecordingPredictor], station_id: str, expected_status: int
) -> None:
    app, predictor = prediction_app
    payload = prediction_payload("UNSUPPORTED-CONNECTOR")
    payload["station_id"] = station_id
    with TestClient(app) as client:
        response = client.post("/api/predict", json=payload)
    assert response.status_code == expected_status
    assert predictor.calls == []
    if expected_status == 404:
        assert response.json()["code"] == "STATION_NOT_FOUND"


@pytest.mark.parametrize(
    "changes",
    [
        {"observed_at": "2026-10-13T09:00:00+00:00"},
        {"observed_at": "2026-10-13T16:01:00+07:00"},
        {"eta": "2026-10-13T16:31:00+07:00"},
        {"eta": "2026-10-13T16:00:00+07:00"},
        {"eta": "2026-10-13T17:05:00+07:00"},
    ],
)
def test_predict_time_validation_still_precedes_inference(
    prediction_app: tuple[FastAPI, RecordingPredictor], changes: dict[str, str]
) -> None:
    app, predictor = prediction_app
    with TestClient(app) as client:
        response = client.post("/api/predict", json={**prediction_payload(), **changes})
    assert response.status_code == 422
    assert predictor.calls == []


@pytest.mark.parametrize("connector, expected_status", [("CCS2", 200), ("Type2", 422)])
def test_predict_single_connector_station_uses_its_own_capabilities(
    prediction_app: tuple[FastAPI, RecordingPredictor], connector: str, expected_status: int
) -> None:
    app, predictor = prediction_app
    payload = {**prediction_payload(connector), "station_id": "S002"}
    with TestClient(app) as client:
        response = client.post("/api/predict", json=payload)
    assert response.status_code == expected_status
    assert len(predictor.calls) == (1 if expected_status == 200 else 0)


@pytest.mark.parametrize(
    "error, expected_status",
    [(ModelNotReadyError("predictor unavailable"), 503), (ValueError("internal defect"), 500)],
)
def test_predict_does_not_mask_dependency_or_internal_errors(
    prediction_app: tuple[FastAPI, RecordingPredictor],
    error: Exception,
    expected_status: int,
) -> None:
    app, _ = prediction_app

    class UnavailablePredictor:
        def predict(self, request: PredictRequest) -> PredictionResult:
            raise error

    app.state.container.predictors_by_scenario[Scenario.TET] = UnavailablePredictor()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/predict", json=prediction_payload())
    assert response.status_code == expected_status
    if expected_status == 503:
        assert response.json()["code"] == "MODEL_NOT_READY"


def test_recommend_uses_real_coordinator_not_phase_zero_facade() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/recommend",
        json={
            "request_id": "real-route-1",
            "origin": {"lat": 10.78, "lng": 106.70},
            "destination": {"lat": 10.35, "lng": 107.08},
            "observed_at": "2026-10-13T16:00:00+07:00",
            "depart_time": "2026-10-13T16:00:00+07:00",
            "scenario": "normal",
            "vehicle": {
                "soc_pct": 80,
                "battery_kwh": 60,
                "consumption_kwh_per_km": 0.18,
                "connector_type": "CCS2",
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["allocation_method"] != "phase0_placeholder"


def test_reset_delegates_to_real_allocation_state() -> None:
    client = TestClient(create_app())
    assert client.post("/api/reset", json={}).json()["reset"] is True


def test_predict_and_pressure_use_scenario_predictor() -> None:
    calls = []

    class Predictor:
        def predict(self, request):
            calls.append(request)
            return PredictionResult(
                station_id=request.station_id,
                eta=request.eta,
                p_available=0.4,
                reasons=["test"],
                explanation_method="rule",
                model_version="test-v1",
                data_type=DataType.MOCK,
            )

    app = create_app()
    app.state.container.predictors_by_scenario[Scenario.TET] = Predictor()
    client = TestClient(app)
    timestamp = "2026-10-13T16:00:00+07:00"
    prediction = client.post(
        "/api/predict",
        json={
            "station_id": "S001",
            "observed_at": timestamp,
            "eta": "2026-10-13T16:30:00+07:00",
            "connector_type": "CCS2",
            "scenario": "tet",
        },
    )
    pressure = client.get("/api/pressure", params={"scenario": "tet", "time": timestamp})
    assert prediction.json()["p_available"] == 0.4
    assert pressure.status_code == 200
    assert all(item["pressure_score"] == 0.6 for item in pressure.json()["stations"])
    assert len(calls) == len(pressure.json()["stations"]) + 1


async def test_http_retry_conflict_and_reset_preserve_exactly_one_primary_allocation() -> None:
    app = create_app(
        Settings(
            data_backend="mock",
            predictor_backend="fake",
            route_backend="fake",
            data_dir=Path(__file__).resolve().parents[2] / "modules" / "station_data",
            expected_virtual_load=1.0,
            assumed_charge_duration_minutes=60,
            virtual_load_receipt_ttl_seconds=1800,
            fake_prediction_horizon_minutes=60,
            min_arrival_soc_pct=10,
        )
    )
    store = app.state.container.virtual_load_store
    payload = recommendation_payload("c9-load-evidence")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.post("/api/reset", json={})).json()["reset"] is True
            first = await client.post("/api/recommend", json=payload)
            assert first.status_code == 200
            body = first.json()
            assert body["primary"] is not None
            eta = datetime.fromisoformat(body["primary"]["eta"])
            station_id = body["primary"]["station_id"]
            expected = {station_id: 1.0}
            assert await store.snapshot(eta, Scenario.NORMAL) == expected
            replay = await client.post("/api/recommend", json=payload)
            assert replay.status_code == 200 and replay.json() == body
            assert await store.snapshot(eta, Scenario.NORMAL) == expected
            changed = {**payload, "scenario": "tet"}
            conflict = await client.post("/api/recommend", json=changed)
            assert conflict.status_code == 409
            assert conflict.json()["code"] == "REQUEST_CONFLICT"
            assert await store.snapshot(eta, Scenario.NORMAL) == expected
            assert await store.snapshot(eta, Scenario.TET) == {}
            assert (await client.post("/api/reset", json={})).json()["reset"] is True
            assert await store.snapshot(eta, Scenario.NORMAL) == {}
            reused = await client.post("/api/recommend", json=changed)
            assert reused.status_code == 200
            reused_eta = datetime.fromisoformat(reused.json()["primary"]["eta"])
            assert await store.snapshot(reused_eta, Scenario.TET) == {
                reused.json()["primary"]["station_id"]: 1.0
            }
            assert await store.snapshot(eta, Scenario.NORMAL) == {}
