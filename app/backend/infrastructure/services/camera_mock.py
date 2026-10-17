"""Mock station cameras: queue counts that follow time of day and scenario.

No video is processed. This stands in for the output of a camera counting
vehicles at a station; a real feed would implement the same
``QueueObservationSource`` port. Output is deterministic for a seed so demos
reproduce, and ``camera_mock.json`` can force a jam or remove a camera.
"""

import hashlib
import json
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.queue import QueueObservation
from app.backend.contracts.stations import Station

_DEFAULT_CONFIG = Path(__file__).with_name("camera_mock.json")
_LOCAL = timezone(timedelta(hours=7))
_BUCKET_MINUTES = 5
_SCENARIO_LOAD = {Scenario.NORMAL: 1.0, Scenario.HOLIDAY_30_4: 1.5, Scenario.TET: 2.0}
# Demand by local hour: quiet at night, commuter peaks at 7-9 and 17-20.
_HOURLY_DEMAND = (
    0.05, 0.05, 0.05, 0.05, 0.08, 0.15, 0.4, 0.7, 0.75, 0.55, 0.45, 0.45,
    0.5, 0.45, 0.4, 0.45, 0.6, 0.9, 1.0, 0.9, 0.6, 0.35, 0.2, 0.1,
)  # fmt: skip
_OVERRIDE_FIELDS = {"vehicles_waiting", "vehicles_charging", "confidence"}


def _unit(*parts: object) -> float:
    """Stable pseudo-random number in [0, 1) from the given parts."""
    digest = hashlib.sha256(":".join(str(part) for part in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


class MockCameraQueueSource:
    def __init__(
        self,
        stations: Iterable[Station],
        *,
        seed: int | None = None,
        coverage: float | None = None,
        config_path: Path | None = None,
    ) -> None:
        config: dict[str, Any] = json.loads((config_path or _DEFAULT_CONFIG).read_text())
        self._ports = {station.station_id: station.n_ports for station in stations}
        self._seed = int(config["seed"] if seed is None else seed)
        share = float(config["coverage"] if coverage is None else coverage)
        if not 0 <= share <= 1:
            raise ValueError("coverage must be between 0 and 1")
        forced = set(config.get("force_camera", []))
        removed = set(config.get("no_camera", []))
        self._overrides: dict[str, dict[str, Any]] = config.get("overrides", {})
        for station_id in forced | removed | set(self._overrides):
            if station_id not in self._ports:
                raise ValueError(f"camera config names unknown station: {station_id}")
        for station_id, values in self._overrides.items():
            if not set(values) <= _OVERRIDE_FIELDS:
                raise ValueError(f"unsupported override fields for {station_id}")
        self._cameras = {
            station_id
            for station_id in self._ports
            if station_id in forced
            or (station_id not in removed and _unit(self._seed, "camera", station_id) < share)
        }

    def has_camera(self, station_id: str) -> bool:
        return station_id in self._cameras

    def observe(self, station_id: str, at: datetime, scenario: Scenario) -> QueueObservation | None:
        if station_id not in self._cameras:
            return None
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("at must be timezone-aware")
        local = at.astimezone(_LOCAL)
        observed_at = local.replace(
            minute=local.minute // _BUCKET_MINUTES * _BUCKET_MINUTES, second=0, microsecond=0
        )
        ports = self._ports[station_id]
        override = self._overrides.get(station_id)
        if override is not None:
            waiting = int(override.get("vehicles_waiting", 0))
            charging = int(override.get("vehicles_charging", 0))
            confidence = float(override.get("confidence", 1.0))
        else:
            stamp = observed_at.isoformat()
            demand = _HOURLY_DEMAND[observed_at.hour] * _SCENARIO_LOAD[Scenario(scenario)]
            station_factor = 0.6 + 0.8 * _unit(self._seed, "station", station_id)
            noise = _unit(self._seed, "noise", station_id, stamp, scenario) - 0.5
            waiting = max(0, round(ports * 0.6 * demand * station_factor + 2 * noise))
            charging = min(ports, round(ports * min(1.0, 0.1 + 0.8 * demand)))
            confidence = self._confidence(station_id, stamp)
        return QueueObservation(
            station_id=station_id,
            observed_at=observed_at,
            vehicles_waiting=waiting,
            vehicles_charging=charging,
            confidence=confidence,
            source="camera_mock",
            data_type=DataType.MOCK,
        )

    def _confidence(self, station_id: str, stamp: str) -> float:
        """Most views are clear; about one in seven is poor (glare, occlusion)."""
        roll = _unit(self._seed, "confidence", station_id, stamp)
        if roll < 0.15:
            return 0.3 + 0.3 * (roll / 0.15)
        return 0.75 + 0.25 * ((roll - 0.15) / 0.85)
