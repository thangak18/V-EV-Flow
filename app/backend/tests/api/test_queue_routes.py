from fastapi.testclient import TestClient

from app.backend.api.main import create_app
from app.backend.core.settings import Settings
from app.backend.tests.api.test_mock_api import recommendation_payload

EVENING = "2026-10-17T18:00:00+07:00"


def client(**overrides: object) -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, **overrides)))  # type: ignore[arg-type]


def test_queue_snapshot_is_labeled_mock_and_covers_only_some_stations() -> None:
    http = client()
    body = http.get("/api/stations/queue", params={"observed_at": EVENING}).json()
    station_ids = {item["station_id"] for item in http.get("/api/stations").json()["stations"]}
    seen = [item["station_id"] for item in body["observations"]]
    assert body["data_type"] == "mock"
    assert any("mock" in note.lower() for note in body["source_notes"])
    assert seen and set(seen) < station_ids
    assert {item["source"] for item in body["observations"]} == {"camera_mock"}


def test_queue_snapshot_follows_scenario() -> None:
    http = client()

    def waiting(scenario: str) -> int:
        body = http.get(
            "/api/stations/queue", params={"observed_at": EVENING, "scenario": scenario}
        ).json()
        return sum(item["vehicles_waiting"] for item in body["observations"])

    assert waiting("tet") > waiting("normal")


def test_queue_snapshot_defaults_to_now_and_normal() -> None:
    response = client().get("/api/stations/queue")
    assert response.status_code == 200
    assert response.json()["scenario"] == "normal"
    assert response.json()["observed_at"].endswith("+07:00")


def test_disabled_backend_reports_no_cameras_without_failing() -> None:
    body = client(camera_queue_backend="off").get("/api/stations/queue").json()
    assert body["observations"] == []
    assert any("disabled" in note.lower() for note in body["source_notes"])


def test_naive_time_and_unknown_scenario_are_rejected() -> None:
    http = client()
    assert (
        http.get("/api/stations/queue", params={"observed_at": "2026-10-17T18:00:00"}).status_code
        == 422
    )
    assert http.get("/api/stations/queue", params={"scenario": "nope"}).status_code == 422


def test_recommendation_explains_queue_source_when_cameras_are_on() -> None:
    reasons = client().post("/api/recommend", json=recommendation_payload()).json()["reasons"]
    assert any("Primary" in reason and "expected wait" in reason for reason in reasons)


def test_recommendation_has_no_queue_reasons_when_cameras_are_off() -> None:
    reasons = (
        client(camera_queue_backend="off")
        .post("/api/recommend", json=recommendation_payload())
        .json()["reasons"]
    )
    assert not any("expected wait" in reason for reason in reasons)
