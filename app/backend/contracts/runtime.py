"""Capabilities and canonical partner ingestion, separate from simulation provenance."""

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from .common import StrictModel
from .enums import DataType, Scenario
from .stations import StationStatus


class RuntimeContext(StrictModel):
    clock_mode: Literal["mock", "replay", "live"]
    scenario: Scenario
    data_type: DataType
    observed_at: datetime | None
    history_start: datetime | None
    history_end: datetime | None
    max_horizon_minutes: int
    places_available: bool
    available: bool
    message: str
    allocation_backend: Literal["memory", "sqlite"]


class PartnerSnapshot(StationStatus):
    ports_free: int = Field(ge=0, strict=True)
    ports_busy: int = Field(ge=0, strict=True)
    ports_broken: int = Field(ge=0, strict=True)
    n_ports: int = Field(ge=1, strict=True)


class SnapshotBatch(StrictModel):
    snapshots: tuple[PartnerSnapshot, ...] = Field(min_length=1, max_length=1000)

    @field_validator("snapshots")
    @classmethod
    def unique_keys(cls, rows: tuple[PartnerSnapshot, ...]) -> tuple[PartnerSnapshot, ...]:
        keys = {(row.station_id, row.scenario, row.ts) for row in rows}
        if len(keys) != len(rows):
            raise ValueError("snapshot batch contains duplicate keys")
        return rows


class IngestResult(StrictModel):
    accepted: int
    source: str
    data_type: Literal["real"] = "real"
