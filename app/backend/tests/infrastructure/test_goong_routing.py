"""Behavior tests for the Goong Directions V2 routing adapter."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app.backend.contracts.common import Coordinate
from app.backend.contracts.errors import RouteUnavailableError
from app.backend.contracts.ports import RouteProvider
from app.backend.contracts.recommendation import RouteRequest, Vehicle
from app.backend.infrastructure.routing.cache import RouteCache
from app.backend.infrastructure.services import FakeRouteProvider

POLYLINE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
POLYLINE_POINTS = (
    Coordinate(lat=38.5, lng=-120.2),
    Coordinate(lat=40.7, lng=-120.95),
    Coordinate(lat=43.252, lng=-126.453),
)
NOW = datetime(2026, 10, 13, 8, tzinfo=timezone(timedelta(hours=7)))
SECRET = "secret-never-leak"


def valid_route(distance_m: float = 1250, duration_s: float = 90) -> dict[str, object]:
    return {
        "legs": [{"distance": {"value": distance_m}, "duration": {"value": duration_s}}],
        "overview_polyline": {"points": POLYLINE},
    }


def valid_request() -> RouteRequest:
    return RouteRequest(
        origin=Coordinate(lat=10.7, lng=106.6),
        destination=Coordinate(lat=10.8, lng=106.8),
        depart_time=NOW,
        vehicle=Vehicle(
            soc_pct=80,
            battery_kwh=60,
            consumption_kwh_per_km=0.18,
            connector_type="CCS2",
        ),
    )


def make_provider(tmp_path: Path, client: httpx.AsyncClient):
    from app.backend.infrastructure.routing.goong import GoongRouteProvider

    return GoongRouteProvider(
        api_key=SECRET,
        client=client,
        cache=RouteCache(tmp_path / "route-cache", timedelta(minutes=5)),
        clock=lambda: NOW,
    )


@pytest.mark.asyncio
async def test_formats_v2_request_and_normalizes_route(tmp_path: Path) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"routes": [valid_route(distance_m=1250, duration_s=90)]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        routes = await make_provider(tmp_path, client).get_routes(valid_request())
        assert not client.is_closed

    assert captured[0].url.params["origin"] == "10.7,106.6"
    assert captured[0].url.params["destination"] == "10.8,106.8"
    assert captured[0].url.params["vehicle"] == "car"
    assert captured[0].url.params["api_key"] == SECRET
    assert routes[0].distance_km == pytest.approx(1.25)
    assert routes[0].duration_minutes == pytest.approx(1.5)
    assert routes[0].source == "goong-directions-v2"
    assert routes[0].geometry == POLYLINE_POINTS


@pytest.mark.asyncio
async def test_sums_legs_and_keeps_alternative_order(tmp_path: Path) -> None:
    payload = {
        "routes": [
            {
                "legs": [
                    {"distance": {"value": 100}, "duration": {"value": 60}},
                    {"distance": {"value": 400}, "duration": {"value": 180}},
                ]
            },
            valid_route(distance_m=2000, duration_s=600),
        ]
    }

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        routes = await make_provider(tmp_path, client).get_routes(valid_request())

    assert [(route.distance_km, route.duration_minutes) for route in routes] == [
        (0.5, 4.0),
        (2.0, 10.0),
    ]
    assert routes[0].geometry is None
    assert routes[1].geometry == POLYLINE_POINTS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"routes": []},
        {"routes": [{"legs": []}]},
        {"routes": [{"legs": [{"distance": {"value": -1}, "duration": {"value": 1}}]}]},
        {"routes": [{"legs": [{"distance": {}, "duration": {"value": 1}}]}]},
        {"routes": [{"legs": [{"distance": {"value": "1250"}, "duration": {"value": 1}}]}]},
        {"routes": [{"legs": [{"distance": {"value": 1}, "duration": {}}]}]},
        {"routes": [{"legs": [{"distance": {"value": 1}, "duration": {"value": "90"}}]}]},
    ],
)
async def test_rejects_unusable_upstream_payload(
    tmp_path: Path, payload: dict[str, object]
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable") as error:
            await make_provider(tmp_path, client).get_routes(valid_request())

    assert SECRET not in str(error.value)


@pytest.mark.asyncio
async def test_rejects_non_finite_upstream_numeric_values(tmp_path: Path) -> None:
    content = (
        b'{"routes":[{"legs":[{"distance":{"value":NaN},'
        b'"duration":{"value":Infinity}}]}]}'
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=content)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable"):
            await make_provider(tmp_path, client).get_routes(valid_request())


@pytest.mark.asyncio
async def test_rejects_malformed_present_polyline(tmp_path: Path) -> None:
    payload = valid_route()
    payload["overview_polyline"] = {"points": "\x7f"}

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"routes": [payload]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable"):
            await make_provider(tmp_path, client).get_routes(valid_request())


@pytest.mark.asyncio
async def test_rejects_invalid_json(tmp_path: Path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable"):
            await make_provider(tmp_path, client).get_routes(valid_request())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "make_error",
    [
        lambda request: httpx.TimeoutException("upstream error", request=request),
        lambda request: httpx.ConnectError("upstream error", request=request),
    ],
)
async def test_normalizes_transport_errors(
    tmp_path: Path, make_error: Callable[[httpx.Request], httpx.HTTPError]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise make_error(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable") as error:
            await make_provider(tmp_path, client).get_routes(valid_request())

    assert SECRET not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 429, 500, 503])
async def test_normalizes_unsuccessful_statuses(tmp_path: Path, status_code: int) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=f"upstream response contains {SECRET}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable") as error:
            await make_provider(tmp_path, client).get_routes(valid_request())

    assert SECRET not in str(error.value)


def test_rejects_blank_api_key_at_construction(tmp_path: Path) -> None:
    from app.backend.infrastructure.routing.goong import GoongRouteProvider

    client = httpx.AsyncClient()
    try:
        with pytest.raises(ValueError, match="api_key"):
            GoongRouteProvider(
                api_key="  ",
                client=client,
                cache=RouteCache(tmp_path / "route-cache", timedelta(minutes=5)),
                clock=lambda: NOW,
            )
    finally:
        import asyncio

        asyncio.run(client.aclose())


def test_route_providers_conform_to_frozen_port(tmp_path: Path) -> None:
    from app.backend.infrastructure.routing.goong import GoongRouteProvider

    client = httpx.AsyncClient()
    try:
        provider = GoongRouteProvider(
            api_key=SECRET,
            client=client,
            cache=RouteCache(tmp_path / "route-cache", timedelta(minutes=5)),
            clock=lambda: NOW,
        )
        assert isinstance(provider, RouteProvider)
        assert isinstance(FakeRouteProvider(), RouteProvider)
    finally:
        import asyncio

        asyncio.run(client.aclose())
