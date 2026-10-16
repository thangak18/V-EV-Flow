from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.backend.api.main import create_app
from app.backend.contracts.common import Coordinate
from app.backend.contracts.errors import RouteUnavailableError
from app.backend.contracts.recommendation import RouteResult
from app.backend.core.settings import Settings

PAYLOAD = {
    "origin": {"lat": 10.78, "lng": 106.7},
    "destination": {"lat": 10.8, "lng": 106.9},
    "depart_time": "2026-10-13T16:00:00+07:00",
}


def test_map_routes_returns_provider_geometry_without_allocating() -> None:
    app = create_app(Settings())
    provider = AsyncMock(
        return_value=(
            RouteResult(
                distance_km=25,
                duration_minutes=40,
                source="goong-directions-v2",
                geometry=(Coordinate(lat=10.78, lng=106.7), Coordinate(lat=10.8, lng=106.9)),
            ),
        )
    )
    app.state.container.routes.get_routes = provider
    recommend = AsyncMock()
    app.state.container.allocation_coordinator.recommend = recommend
    with TestClient(app) as client:
        response = client.post("/api/routes", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json()[0]["geometry"] == [PAYLOAD["origin"], PAYLOAD["destination"]]
    assert provider.call_args.args[0].origin.lat == 10.78
    recommend.assert_not_called()


def test_map_routes_empty_invalid_and_unavailable() -> None:
    app = create_app(Settings())
    provider = AsyncMock(return_value=())
    app.state.container.routes.get_routes = provider
    with TestClient(app) as client:
        assert client.post("/api/routes", json=PAYLOAD).json() == []
        provider.reset_mock()
        assert (
            client.post(
                "/api/routes", json={**PAYLOAD, "origin": {"lat": 999, "lng": 0}}
            ).status_code
            == 422
        )
        provider.assert_not_called()
        provider.side_effect = RouteUnavailableError("Routing temporarily unavailable")
        response = client.post("/api/routes", json=PAYLOAD)
        assert response.status_code == 503
        assert response.json()["code"] == "ROUTE_UNAVAILABLE"
