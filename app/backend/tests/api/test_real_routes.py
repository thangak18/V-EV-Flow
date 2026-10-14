from datetime import datetime
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.backend.api.main import create_app
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.prediction import PredictionResult
from app.backend.core.settings import Settings
from app.backend.tests.api.test_mock_api import recommendation_payload


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
