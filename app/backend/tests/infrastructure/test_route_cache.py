"""Behavior tests for the versioned disk-backed route cache."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.backend.contracts.common import Coordinate
from app.backend.contracts.recommendation import RouteRequest, RouteResult, Vehicle
from app.backend.infrastructure.routing.cache import RouteCache

UTC_PLUS_7 = timezone(timedelta(hours=7))


def route_request(
    *,
    origin: tuple[float, float],
    destination: tuple[float, float],
    hour: int,
    vehicle: Vehicle | None = None,
) -> RouteRequest:
    return RouteRequest(
        origin=Coordinate(lat=origin[0], lng=origin[1]),
        destination=Coordinate(lat=destination[0], lng=destination[1]),
        depart_time=datetime(2026, 10, 13, hour, tzinfo=UTC_PLUS_7),
        vehicle=vehicle,
    )


@pytest.fixture
def cache(tmp_path: Path) -> RouteCache:
    return RouteCache(tmp_path / "nested" / "route-cache", timedelta(minutes=5))


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 10, 13, 8, tzinfo=UTC_PLUS_7)


@pytest.mark.parametrize("ttl", [timedelta(0), timedelta(seconds=-1)])
def test_rejects_non_positive_ttl_at_construction(tmp_path: Path, ttl: timedelta) -> None:
    with pytest.raises(ValueError, match="ttl"):
        RouteCache(tmp_path / "route-cache", ttl)


def test_key_is_stable_and_direction_time_sensitive(cache: RouteCache) -> None:
    forward = route_request(origin=(10.7, 106.6), destination=(10.8, 106.8), hour=8)
    repeated = route_request(origin=(10.7, 106.6), destination=(10.8, 106.8), hour=8)
    reverse = route_request(origin=(10.8, 106.8), destination=(10.7, 106.6), hour=8)
    later = route_request(origin=(10.7, 106.6), destination=(10.8, 106.8), hour=9)
    different_vehicle = route_request(
        origin=(10.7, 106.6),
        destination=(10.8, 106.8),
        hour=8,
        vehicle=Vehicle(
            soc_pct=85,
            battery_kwh=90,
            consumption_kwh_per_km=0.14,
            connector_type="CHAdeMO",
        ),
    )

    key = cache.key_for(forward)

    assert key == cache.key_for(repeated)
    assert key != cache.key_for(reverse)
    assert key != cache.key_for(later)
    assert key == cache.key_for(different_vehicle)
    assert len(key) == 64
    assert all(character in "0123456789abcdef" for character in key)


def test_returns_valid_routes_only_before_expiry(cache: RouteCache, now: datetime) -> None:
    routes = (RouteResult(distance_km=12.5, duration_minutes=20, source="goong-directions-v2"),)
    key = "a" * 64
    cache.put(key, routes, now, now + timedelta(minutes=5))

    assert cache.get(key, now + timedelta(minutes=4, seconds=59)) == routes
    assert cache.get(key, now + timedelta(minutes=5)) is None


def test_put_creates_nested_directory_and_persists_only_validated_route_data(
    cache: RouteCache, now: datetime
) -> None:
    key = "b" * 64
    routes = (RouteResult(distance_km=12.5, duration_minutes=20, source="goong-directions-v2"),)

    cache.put(key, routes, now, now + timedelta(minutes=5))

    entry = cache.directory / f"{key}.json"
    stored = json.loads(entry.read_text(encoding="utf-8"))
    serialized = entry.read_text(encoding="utf-8")
    assert entry.exists()
    assert stored == {
        "schema_version": 1,
        "key": key,
        "collected_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=5)).isoformat(),
        "routes": [route.model_dump(mode="json") for route in routes],
    }
    assert "api_key" not in serialized
    assert "GOONG_REST_API_KEY" not in serialized
    assert "payload" not in stored


@pytest.mark.parametrize(
    "entry",
    [
        "{broken json",
        {
            "schema_version": 2,
            "key": "c" * 64,
            "collected_at": "2026-10-13T08:00:00+07:00",
            "expires_at": "2026-10-13T08:05:00+07:00",
            "routes": [],
        },
        {
            "schema_version": 1,
            "key": "d" * 64,
            "collected_at": "2026-10-13T08:00:00+07:00",
            "expires_at": "2026-10-13T08:05:00+07:00",
            "routes": [],
        },
        {
            "schema_version": 1,
            "key": "c" * 64,
            "collected_at": "2026-10-13T08:05:00+07:00",
            "expires_at": "2026-10-13T08:00:00+07:00",
            "routes": [],
        },
        {
            "schema_version": 1,
            "key": "c" * 64,
            "collected_at": "2026-10-13T08:00:00",
            "expires_at": "2026-10-13T08:05:00",
            "routes": [],
        },
        {
            "schema_version": 1,
            "key": "c" * 64,
            "collected_at": "2026-10-13T08:00:00+07:00",
            "expires_at": "2026-10-13T08:05:00+07:00",
            "routes": [{"distance_km": -1, "duration_minutes": 20, "source": "goong"}],
        },
    ],
    ids=[
        "corrupt",
        "wrong-schema",
        "wrong-key",
        "invalid-timestamp-order",
        "naive-time",
        "invalid-route",
    ],
)
def test_discards_malformed_or_invalid_entries(
    cache: RouteCache, now: datetime, entry: str | dict[str, object]
) -> None:
    key = "c" * 64
    cache.directory.mkdir(parents=True)
    path = cache.directory / f"{key}.json"
    path.write_text(entry if isinstance(entry, str) else json.dumps(entry), encoding="utf-8")

    assert cache.get(key, now) is None
    assert not path.exists()


def test_discards_stale_entry_even_if_stored_expiry_is_future(
    cache: RouteCache, now: datetime
) -> None:
    key = "e" * 64
    cache.put(key, (), now - timedelta(minutes=6), now - timedelta(seconds=1))
    path = cache.directory / f"{key}.json"

    assert cache.get(key, now) is None
    assert not path.exists()
