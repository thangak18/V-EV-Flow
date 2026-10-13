"""Versioned, disk-backed storage for Goong route results."""

import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timedelta
from itertools import chain, islice
from pathlib import Path
from typing import Any

from app.backend.contracts.recommendation import RouteRequest, RouteResult

_SCHEMA_VERSION = 1
_PROVIDER_VERSION = "goong-directions-v2"
_CLEANUP_SCAN_LIMIT = 32


class RouteCache:
    """Persist validated route alternatives under stable, versioned keys."""

    def __init__(self, directory: Path, ttl: timedelta) -> None:
        if ttl <= timedelta(0):
            raise ValueError("cache ttl must be positive")
        self.directory = directory
        self._ttl = ttl
        self._cleanup_cursor: str | None = None

    @property
    def ttl(self) -> timedelta:
        return self._ttl

    def key_for(self, request: RouteRequest) -> str:
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "provider": _PROVIDER_VERSION,
            "origin": request.origin.model_dump(mode="json"),
            "destination": request.destination.model_dump(mode="json"),
            "depart_time": request.depart_time.isoformat(),
            "vehicle": "car",
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get(self, key: str, now: datetime) -> tuple[RouteResult, ...] | None:
        path = self._path_for(key)
        try:
            with path.open(encoding="utf-8") as entry_file:
                entry = json.load(entry_file, parse_constant=_reject_nonfinite_json)
            routes = self._validate_entry(entry, key, now)
        except FileNotFoundError:
            return None
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            self._unlink(path)
            return None
        return routes

    def put(
        self,
        key: str,
        routes: tuple[RouteResult, ...],
        collected_at: datetime,
        expires_at: datetime,
    ) -> None:
        if not _is_aware(collected_at) or not _is_aware(expires_at):
            raise ValueError("cache timestamps must be timezone-aware")
        if expires_at <= collected_at:
            raise ValueError("cache expiry must be after collection")
        _validate_routes(routes)

        self.directory.mkdir(parents=True, exist_ok=True)
        self._cleanup_expired(collected_at)
        entry = {
            "schema_version": _SCHEMA_VERSION,
            "key": key,
            "collected_at": collected_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "routes": [route.model_dump(mode="json") for route in routes],
        }
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.directory,
                prefix=f".{key}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(entry, temporary_file, allow_nan=False, separators=(",", ":"))
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self._path_for(key))
        except BaseException:
            if temporary_path is not None:
                self._unlink(temporary_path)
            raise

    def _path_for(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def _validate_entry(self, entry: Any, key: str, now: datetime) -> tuple[RouteResult, ...]:
        if not isinstance(entry, dict):
            raise ValueError("cache entry must be an object")
        if entry.get("schema_version") != _SCHEMA_VERSION or entry.get("key") != key:
            raise ValueError("cache entry metadata does not match")

        collected_at = _parse_aware_datetime(entry.get("collected_at"))
        expires_at = _parse_aware_datetime(entry.get("expires_at"))
        if expires_at <= collected_at or expires_at <= now:
            raise ValueError("cache entry is expired or has invalid timestamps")

        raw_routes = entry.get("routes")
        if not isinstance(raw_routes, list):
            raise ValueError("cache routes must be a list")
        routes = tuple(RouteResult.model_validate(route) for route in raw_routes)
        _validate_routes(routes)
        return routes

    def _cleanup_expired(self, now: datetime) -> None:
        """Rotate a bounded cleanup scan so cold entries are eventually reached."""
        try:
            cursor = self._cleanup_cursor
            paths = sorted(self.directory.glob("*.json"), key=lambda path: path.name)
            after_cursor = (path for path in paths if path.name > (cursor or ""))
            before_cursor = (path for path in paths if cursor is not None and path.name <= cursor)
            entries = islice(chain(after_cursor, before_cursor), _CLEANUP_SCAN_LIMIT)
            last_path: Path | None = None
            for path in entries:
                last_path = path
                try:
                    with path.open(encoding="utf-8") as entry_file:
                        entry = json.load(entry_file, parse_constant=_reject_nonfinite_json)
                    expires_at = _parse_aware_datetime(
                        entry.get("expires_at") if isinstance(entry, dict) else None
                    )
                    if expires_at <= now:
                        self._unlink(path)
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    self._unlink(path)
            if last_path is not None:
                self._cleanup_cursor = last_path.name
        except OSError:
            pass

    @staticmethod
    def _unlink(path: Path) -> None:
        try:
            path.unlink()
        except OSError:
            pass


def _parse_aware_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("cache timestamp must be an ISO string")
    parsed = datetime.fromisoformat(value)
    if not _is_aware(parsed):
        raise ValueError("cache timestamp must be timezone-aware")
    return parsed


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _validate_routes(routes: tuple[RouteResult, ...]) -> None:
    if not routes:
        raise ValueError("cache routes must not be empty")
    for route in routes:
        if not math.isfinite(route.distance_km) or not math.isfinite(route.duration_minutes):
            raise ValueError("cache route distance and duration must be finite")


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")
