from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .common import StrictModel
from .enums import DataType, Scenario


class QueueObservation(StrictModel):
    """Queue seen by a station camera at ``observed_at``; mock until a real feed exists."""

    station_id: str = Field(min_length=1)
    observed_at: datetime
    vehicles_waiting: int = Field(ge=0)
    vehicles_charging: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    source: str = Field(min_length=1)
    data_type: DataType

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class QueueSnapshotResponse(StrictModel):
    """Camera views at one moment; stations without a camera are absent."""

    observed_at: datetime
    scenario: Scenario
    observations: tuple[QueueObservation, ...]
    data_type: DataType
    source_notes: list[str]

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def one_view_per_station(self) -> "QueueSnapshotResponse":
        ids = [item.station_id for item in self.observations]
        if len(ids) != len(set(ids)):
            raise ValueError("each station may appear once")
        return self
