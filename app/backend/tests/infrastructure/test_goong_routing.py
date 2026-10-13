"""Behavior tests for the Goong Directions V2 routing adapter."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from app.backend.contracts.common import Coordinate
from app.backend.contracts.errors import RouteUnavailableError
from app.backend.contracts.ports import RouteProvider
from app.backend.contracts.recommendation import RouteRequest, RouteResult, Vehicle
from app.backend.infrastructure.routing.cache import RouteCache
from app.backend.infrastructure.services import FakeRouteProvider

POLYLINE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
POLYLINE_POINTS = (
    Coordinate(lat=38.5, lng=-120.2),
    Coordinate(lat=40.7, lng=-120.95),
    Coordinate(lat=43.252, lng=-126.453),
)
NOW = datetime(2026, 10, 13, 8, tzinfo=timezone(timedelta(hours=7)))
TEST_GOONG_KEY = "not-a-real-goong-key"


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


def make_provider(
    tmp_path: Path,
    client: httpx.AsyncClient,
    *,
    cache: RouteCache | None = None,
    clock: Callable[[], datetime] = lambda: NOW,
):
    from app.backend.infrastructure.routing.goong import GoongRouteProvider

    return GoongRouteProvider(
        api_key=TEST_GOONG_KEY,
        client=client,
        cache=cache or RouteCache(tmp_path / "route-cache", timedelta(minutes=5)),
        clock=clock,
    )


@pytest.mark.asyncio
async def test_cached_route_avoids_second_upstream_call(tmp_path: Path) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"routes": [valid_route()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = make_provider(tmp_path, client)
        first = await provider.get_routes(valid_request())
        second = await provider.get_routes(valid_request())

    assert first == second
    assert calls == 1


@pytest.mark.asyncio
async def test_expired_route_is_fetched_again(tmp_path: Path) -> None:
    calls = 0
    current_time = [NOW]
    cache = RouteCache(tmp_path / "route-cache", timedelta(minutes=5))
    request = valid_request()

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"routes": [valid_route(distance_m=1000 * calls)]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = make_provider(tmp_path, client, cache=cache, clock=lambda: current_time[0])
        first = await provider.get_routes(request)
        assert cache.get(cache.key_for(request), NOW) == first
        current_time[0] += timedelta(minutes=5)
        second = await provider.get_routes(request)

    assert first[0].distance_km == 1
    assert second[0].distance_km == 2
    assert calls == 2


@pytest.mark.asyncio
async def test_corrupted_route_is_replaced_from_upstream(tmp_path: Path) -> None:
    calls = 0
    cache = RouteCache(tmp_path / "route-cache", timedelta(minutes=5))
    request = valid_request()

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"routes": [valid_route()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = make_provider(tmp_path, client, cache=cache)
        entry = cache.directory / f"{cache.key_for(request)}.json"
        cache.directory.mkdir(parents=True)
        entry.write_text("{broken json", encoding="utf-8")

        replacement = await provider.get_routes(request)

    assert replacement[0].distance_km == pytest.approx(1.25)
    assert cache.get(cache.key_for(request), NOW) == replacement
    assert calls == 1


@pytest.mark.asyncio
async def test_failed_upstream_response_is_not_cached(tmp_path: Path) -> None:
    calls = 0
    cache = RouteCache(tmp_path / "route-cache", timedelta(minutes=5))

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, text="unavailable")
        return httpx.Response(200, json={"routes": [valid_route()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = make_provider(tmp_path, client, cache=cache)
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable"):
            await provider.get_routes(valid_request())
        assert list(cache.directory.glob("*.json")) == []
        recovered = await provider.get_routes(valid_request())
        cached = await provider.get_routes(valid_request())

    assert recovered == cached
    assert calls == 2


@pytest.mark.asyncio
async def test_identical_concurrent_requests_share_one_call(tmp_path: Path) -> None:
    calls = 0
    entered = asyncio.Event()
    release = asyncio.Event()

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return httpx.Response(200, json={"routes": [valid_route()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = make_provider(tmp_path, client)
        first = asyncio.create_task(provider.get_routes(valid_request()))
        await entered.wait()
        second = asyncio.create_task(provider.get_routes(valid_request()))
        release.set()

        assert (await first) == (await second)

    assert calls == 1


@pytest.mark.asyncio
async def test_cache_write_failure_returns_route_and_next_request_refetches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0
    cache = RouteCache(tmp_path / "route-cache", timedelta(minutes=5))
    original_put = cache.put
    put_attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"routes": [valid_route()]})

    def fail_first_put(
        key: str,
        routes: tuple[RouteResult, ...],
        collected_at: datetime,
        expires_at: datetime,
    ) -> None:
        nonlocal put_attempts
        put_attempts += 1
        if put_attempts == 1:
            raise OSError("disk unavailable")
        original_put(key, routes, collected_at, expires_at)

    monkeypatch.setattr(cache, "put", fail_first_put)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = make_provider(tmp_path, client, cache=cache)
        first = await provider.get_routes(valid_request())
        second = await provider.get_routes(valid_request())
        third = await provider.get_routes(valid_request())

    assert first == second == third
    assert calls == 2


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
    assert captured[0].url.params["api_key"] == TEST_GOONG_KEY
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

    assert TEST_GOONG_KEY not in str(error.value)


@pytest.mark.asyncio
async def test_rejects_non_finite_upstream_numeric_values(tmp_path: Path) -> None:
    content = b'{"routes":[{"legs":[{"distance":{"value":NaN},"duration":{"value":Infinity}}]}]}'

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=content)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable"):
            await make_provider(tmp_path, client).get_routes(valid_request())


@pytest.mark.asyncio
async def test_normalizes_numeric_conversion_overflow(tmp_path: Path) -> None:
    payload = {"routes": [{"legs": [{"distance": {"value": 10**400}, "duration": {"value": 1}}]}]}

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable"):
            await make_provider(tmp_path, client).get_routes(valid_request())


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["distance", "duration"])
async def test_normalizes_overflow_when_summing_finite_legs(tmp_path: Path, field: str) -> None:
    overflowing: dict[str, float] = {"distance": 1, "duration": 1}
    overflowing[field] = 1e308
    leg = {
        "distance": {"value": overflowing["distance"]},
        "duration": {"value": overflowing["duration"]},
    }
    payload = {
        "routes": [
            {
                "legs": [
                    leg,
                    leg,
                ]
            }
        ]
    }

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

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
async def test_rejects_empty_present_polyline(tmp_path: Path) -> None:
    payload = valid_route()
    payload["overview_polyline"] = {"points": ""}

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"routes": [payload]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable"):
            await make_provider(tmp_path, client).get_routes(valid_request())


def test_rejects_non_ascii_polyline_bytes() -> None:
    from app.backend.infrastructure.routing.goong import _decode_polyline

    with pytest.raises(ValueError, match="invalid character"):
        _decode_polyline("\x7f\x7f")


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

    assert TEST_GOONG_KEY not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 429, 500, 503])
async def test_normalizes_unsuccessful_statuses(tmp_path: Path, status_code: int) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=f"upstream response contains {TEST_GOONG_KEY}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RouteUnavailableError, match="Goong route service unavailable") as error:
            await make_provider(tmp_path, client).get_routes(valid_request())

    assert TEST_GOONG_KEY not in str(error.value)


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
            api_key=TEST_GOONG_KEY,
            client=client,
            cache=RouteCache(tmp_path / "route-cache", timedelta(minutes=5)),
            clock=lambda: NOW,
        )
        assert isinstance(provider, RouteProvider)
        assert isinstance(FakeRouteProvider(), RouteProvider)
    finally:
        import asyncio

        asyncio.run(client.aclose())
