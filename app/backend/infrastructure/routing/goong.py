"""Goong Directions V2 implementation of the frozen route-provider port."""

import asyncio
import math
from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx

from app.backend.contracts.common import Coordinate
from app.backend.contracts.errors import RouteUnavailableError
from app.backend.contracts.recommendation import RouteRequest, RouteResult

from .cache import RouteCache

GOONG_DIRECTIONS_V2_ENDPOINT = "https://rsapi.goong.io/v2/direction"
_UNAVAILABLE_MESSAGE = "Goong route service unavailable"


class GoongRouteProvider:
    """Translate Goong's V2 Directions response into validated route results."""

    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient,
        cache: RouteCache,
        *,
        endpoint: str = GOONG_DIRECTIONS_V2_ENDPOINT,
        clock: Callable[[], datetime],
        timeout: httpx.Timeout = httpx.Timeout(10.0, connect=2.0, read=5.0, write=5.0),
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key must not be blank")
        self._api_key = api_key
        self._client = client
        self._cache = cache
        self._endpoint = endpoint
        self._clock = clock
        self._timeout = timeout
        self._locks: dict[str, asyncio.Lock] = {}
        self._lock_users: dict[str, int] = {}

    async def get_routes(self, request: RouteRequest) -> tuple[RouteResult, ...]:
        key = self._cache.key_for(request)
        cached = self._cache.get(key, self._clock())
        if cached is not None:
            return cached

        lock = self._lock_for(key)
        try:
            async with lock:
                cached = self._cache.get(key, self._clock())
                if cached is not None:
                    return cached

                routes = await self._fetch_routes(request)
                now = self._clock()
                try:
                    self._cache.put(key, routes, now, now + self._cache.ttl)
                except OSError:
                    pass
                return routes
        finally:
            self._release_lock(key, lock)

    def _lock_for(self, key: str) -> asyncio.Lock:
        lock = self._locks.setdefault(key, asyncio.Lock())
        self._lock_users[key] = self._lock_users.get(key, 0) + 1
        return lock

    def _release_lock(self, key: str, lock: asyncio.Lock) -> None:
        remaining_users = self._lock_users[key] - 1
        if remaining_users:
            self._lock_users[key] = remaining_users
            return
        self._lock_users.pop(key)
        if not lock.locked() and self._locks.get(key) is lock:
            self._locks.pop(key)

    async def _fetch_routes(self, request: RouteRequest) -> tuple[RouteResult, ...]:
        origin = _coordinate_text(request.origin)
        destination = _coordinate_text(request.destination)
        try:
            response = await self._client.get(
                self._endpoint,
                params={
                    "origin": origin,
                    "destination": destination,
                    "vehicle": "car",
                    "api_key": self._api_key,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            return _parse_routes(response.json())
        except (httpx.HTTPError, OverflowError, TypeError, ValueError):
            raise RouteUnavailableError(_UNAVAILABLE_MESSAGE) from None


def _coordinate_text(coordinate: Coordinate) -> str:
    if not math.isfinite(coordinate.lat) or not math.isfinite(coordinate.lng):
        raise ValueError("route coordinates must be finite")
    return f"{coordinate.lat},{coordinate.lng}"


def _parse_routes(payload: Any) -> tuple[RouteResult, ...]:
    if not isinstance(payload, dict):
        raise ValueError("routes payload must be an object")
    raw_routes = payload.get("routes")
    if not isinstance(raw_routes, list) or not raw_routes:
        raise ValueError("routes payload must include alternatives")

    routes: list[RouteResult] = []
    for raw_route in raw_routes:
        if not isinstance(raw_route, dict):
            raise ValueError("route alternative must be an object")
        raw_legs = raw_route.get("legs")
        if not isinstance(raw_legs, list) or not raw_legs:
            raise ValueError("route alternative must include legs")

        distance_m = 0.0
        duration_s = 0.0
        for raw_leg in raw_legs:
            if not isinstance(raw_leg, dict):
                raise ValueError("route leg must be an object")
            distance_m = _add_finite(
                distance_m, _nonnegative_number(raw_leg.get("distance"), "distance"), "distance"
            )
            duration_s = _add_finite(
                duration_s, _nonnegative_number(raw_leg.get("duration"), "duration"), "duration"
            )

        geometry = _parse_geometry(raw_route)
        distance_km = distance_m / 1000
        duration_minutes = duration_s / 60
        if not math.isfinite(distance_km) or not math.isfinite(duration_minutes):
            raise ValueError("route units must convert to finite values")
        routes.append(
            RouteResult(
                distance_km=distance_km,
                duration_minutes=duration_minutes,
                geometry=geometry,
                source="goong-directions-v2",
            )
        )
    return tuple(routes)


def _nonnegative_number(container: Any, field_name: str) -> float:
    if not isinstance(container, dict):
        raise ValueError(f"route {field_name} must be an object")
    value = container.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"route {field_name} must be numeric")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0:
        raise ValueError(f"route {field_name} must be finite and non-negative")
    return converted


def _add_finite(total: float, value: float, field_name: str) -> float:
    combined = total + value
    if not math.isfinite(combined):
        raise ValueError(f"route {field_name} total must be finite")
    return combined


def _parse_geometry(raw_route: dict[str, Any]) -> tuple[Coordinate, ...] | None:
    if "overview_polyline" not in raw_route:
        return None
    raw_polyline = raw_route["overview_polyline"]
    if not isinstance(raw_polyline, dict):
        raise ValueError("overview polyline must be an object")
    encoded = raw_polyline.get("points")
    if not isinstance(encoded, str):
        raise ValueError("overview polyline points must be a string")
    if not encoded:
        raise ValueError("overview polyline points must not be empty")
    return _decode_polyline(encoded)


def _decode_polyline(encoded: str) -> tuple[Coordinate, ...]:
    index = 0
    latitude = 0
    longitude = 0
    coordinates: list[Coordinate] = []

    while index < len(encoded):
        latitude_delta, index = _decode_polyline_value(encoded, index)
        longitude_delta, index = _decode_polyline_value(encoded, index)
        latitude += latitude_delta
        longitude += longitude_delta
        try:
            coordinates.append(Coordinate(lat=latitude / 100_000, lng=longitude / 100_000))
        except ValueError as error:
            raise ValueError("overview polyline has invalid coordinates") from error

    return tuple(coordinates)


def _decode_polyline_value(encoded: str, index: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if index >= len(encoded):
            raise ValueError("unterminated encoded polyline value")
        code_point = ord(encoded[index])
        index += 1
        if not 63 <= code_point <= 126:
            raise ValueError("encoded polyline has an invalid character")
        chunk = code_point - 63
        result |= (chunk & 0x1F) << shift
        shift += 5
        if shift > 60:
            raise ValueError("encoded polyline value is too large")
        if not chunk & 0x20:
            break
    return (-(result >> 1) - 1 if result & 1 else result >> 1), index
