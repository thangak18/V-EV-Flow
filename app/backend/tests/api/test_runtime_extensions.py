"""Runtime extensions use mocked provider transports and authenticated canonical feed."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.backend.api.main import create_app
from app.backend.core.settings import Settings


def test_runtime_and_disabled_place_proxy() -> None:
    with TestClient(create_app(Settings())) as client:
        context = client.get("/api/runtime").json()
        assert context["clock_mode"] == "mock"
        assert context["places_available"] is False
        assert client.get("/api/places/search", params={"q": "ab"}).status_code == 503
        assert client.get("/api/places/search", params={"q": " "}).status_code == 422
        assert client.post("/api/partner/snapshots", json={"snapshots": []}).status_code == 422


def test_places_resolve_coordinates_cache_and_redact_errors() -> None:
    calls = []

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        assert request.url.params["api_key"] == "test-credential"
        if request.url.path.endswith("autocomplete"):
            return httpx.Response(
                200,
                json={
                    "status": "OK",
                    "predictions": [{"place_id": "place/one", "description": "Long Thành"}],
                },
            )
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "result": {
                    "place_id": "place/one",
                    "formatted_address": "Long Thành, Đồng Nai",
                    "geometry": {"location": {"lat": 10.8, "lng": 107.01}},
                },
            },
        )

    external = httpx.AsyncClient(transport=httpx.MockTransport(provider))
    app = create_app(
        Settings(places_backend="goong", goong_rest_api_key="test-credential"),
        route_client=external,
    )
    with TestClient(app) as client:
        assert client.get("/api/runtime").json()["places_available"] is True
        suggestions = client.get("/api/places/search", params={"q": "Long Thành"})
        assert suggestions.json()["predictions"][0]["place_id"] == "place/one"
        for _ in range(2):
            detail = client.get("/api/places/detail", params={"place_id": "place/one"})
            assert detail.json()["lat"] == 10.8
            assert "test-credential" not in detail.text
        assert calls == ["/v2/place/autocomplete", "/v2/place/detail"]
    assert not external.is_closed


def test_invalid_provider_data_is_503_not_fake_coordinates() -> None:
    external = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(403, json={"error": "private-provider-details"})
        )
    )
    app = create_app(
        Settings(places_backend="goong", goong_rest_api_key="test"),
        route_client=external,
    )
    with TestClient(app) as client:
        response = client.get("/api/places/detail", params={"place_id": "missing"})
        assert response.status_code == 503
        assert "private-provider-details" not in response.text
        assert "api_key" not in response.text


def partner_app(tmp_path: Path):
    raw = json.loads(Path("app/backend/modules/station_data/fixtures/stations.json").read_text())
    station = raw[0]
    station["source"] = "test-partner"
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "stations.json").write_text(json.dumps([station]))
    settings = Settings(
        data_backend="real",
        data_dir=tmp_path,
        partner_history_path=tmp_path / "partner.sqlite3",
        partner_source="test-partner",
        partner_ingest_token="test-token-" * 4,
    )
    return create_app(settings), station


def test_partner_auth_idempotency_conflict_freshness_and_provenance(tmp_path: Path) -> None:
    app, station = partner_app(tmp_path)
    now = datetime.now(timezone(timedelta(hours=7))).replace(second=0, microsecond=0)
    now = now.replace(minute=now.minute // 5 * 5)
    row = dict(
        station_id=station["station_id"],
        ts=now.isoformat(),
        ports_free=station["n_ports"],
        ports_busy=0,
        ports_broken=0,
        n_ports=station["n_ports"],
        scenario="normal",
    )
    headers = {"Authorization": "Bearer " + "test-token-" * 4}
    with TestClient(app) as client:
        assert client.get("/api/runtime").json()["available"] is False
        assert client.post("/api/partner/snapshots", json={"snapshots": [row]}).status_code == 401
        for _ in range(2):
            assert (
                client.post(
                    "/api/partner/snapshots", headers=headers, json={"snapshots": [row]}
                ).json()["accepted"]
                == 1
            )
        context = client.get("/api/runtime").json()
        assert context["available"] is False and context["clock_mode"] == "live"
        assert context["history_end"] is not None  # feed accepted, fake model cannot serve live
        assert context["data_type"] == "real"
        assert client.get("/api/runtime?scenario=tet").json()["available"] is False
        changed = {**row, "ports_free": row["ports_free"] - 1, "ports_busy": 1}
        assert (
            client.post(
                "/api/partner/snapshots", headers=headers, json={"snapshots": [changed]}
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/partner/snapshots",
                headers=headers,
                json={"snapshots": [{**row, "ports_busy": True}]},
            ).status_code
            == 422
        )
        old = (now - timedelta(hours=2)).isoformat()
        response = client.post(
            "/api/predict",
            json={
                "station_id": station["station_id"],
                "observed_at": old,
                "eta": (now - timedelta(hours=1, minutes=30)).isoformat(),
                "scenario": "normal",
                "connector_type": station["connector_types"][0],
            },
        )
        assert response.status_code == 503 and response.json()["code"] == "DATA_SOURCE_UNAVAILABLE"
