from fastapi.testclient import TestClient

from app.backend.api.main import create_app


def test_station_endpoint_labels_mock_data() -> None:
    response = TestClient(create_app()).get("/api/stations")
    assert response.status_code == 200
    assert response.json()["data_type"] == "mock"


def test_unknown_station_is_404() -> None:
    response = TestClient(create_app()).post("/api/predict", json={
        "station_id": "UNKNOWN", "observed_at": "2026-10-13T16:00:00+07:00",
        "eta": "2026-10-13T16:40:00+07:00", "connector_type": "CCS2",
        "scenario": "normal"
    })
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
