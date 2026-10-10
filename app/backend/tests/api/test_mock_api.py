from fastapi.testclient import TestClient

from app.backend.api.dependencies import StartupConfigurationError
from app.backend.api.main import create_app
from app.backend.core.settings import Settings


def recommendation_payload(request_id: str = "demo-001") -> dict[str, object]:
    return {
        "request_id": request_id,
        "origin": {"lat": 10.78, "lng": 106.70},
        "destination": {"lat": 10.35, "lng": 107.08},
        "observed_at": "2026-10-13T16:00:00+07:00",
        "depart_time": "2026-10-13T16:00:00+07:00",
        "scenario": "normal",
        "vehicle": {
            "soc_pct": 20,
            "battery_kwh": 60,
            "consumption_kwh_per_km": 0.18,
            "connector_type": "CCS2",
        },
    }


def test_station_endpoint_labels_mock_data() -> None:
    response = TestClient(create_app()).get("/api/stations")
    assert response.status_code == 200
    assert response.json()["data_type"] == "mock"


def test_cors_uses_configured_origins() -> None:
    settings = Settings(cors_origins=["https://demo.example"])
    response = TestClient(create_app(settings)).options(
        "/api/health",
        headers={
            "Origin": "https://demo.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers["access-control-allow-origin"] == "https://demo.example"


def test_unknown_station_is_404() -> None:
    response = TestClient(create_app()).post(
        "/api/predict",
        json={
            "station_id": "UNKNOWN",
            "observed_at": "2026-10-13T16:00:00+07:00",
            "eta": "2026-10-13T16:40:00+07:00",
            "connector_type": "CCS2",
            "scenario": "normal",
        },
    )
    assert response.status_code == 404
    assert response.json()["code"] == "STATION_NOT_FOUND"


def test_whatif_is_explicitly_not_ready() -> None:
    response = TestClient(create_app()).post("/api/whatif", json={})
    assert response.status_code == 503
    assert response.json()["code"] == "FEATURE_NOT_READY"


def test_invalid_prediction_is_422() -> None:
    response = TestClient(create_app()).post(
        "/api/predict",
        json={
            "station_id": "S001",
            "observed_at": "2026-10-13T16:00:00+07:00",
            "eta": "2026-10-13T15:00:00+07:00",
            "connector_type": "CCS2",
            "scenario": "normal",
        },
    )
    assert response.status_code == 422


def test_recommendation_conflict_reset_and_success() -> None:
    client = TestClient(create_app())
    result = client.post("/api/recommend", json=recommendation_payload())
    assert result.status_code == 200
    assert result.json()["primary"] is None
    assert result.json()["allocation_method"] == "phase0_placeholder"
    changed = recommendation_payload()
    changed["scenario"] = "tet"
    assert client.post("/api/recommend", json=changed).status_code == 409
    assert client.post("/api/reset", json={}).json()["reset"] is True
    assert client.post("/api/recommend", json=changed).status_code == 200


def test_openapi_declares_domain_error_responses() -> None:
    schema = TestClient(create_app()).get("/openapi.json").json()
    assert "409" in schema["paths"]["/api/recommend"]["post"]["responses"]
    assert "503" in schema["paths"]["/api/whatif"]["post"]["responses"]


def test_unavailable_backend_selection_fails_at_composition() -> None:
    settings = Settings.model_construct(
        data_backend="file", predictor_backend="fake", route_backend="fake"
    )
    try:
        create_app(settings)
    except StartupConfigurationError:
        return
    raise AssertionError("unavailable Phase 0 backend must fail")
