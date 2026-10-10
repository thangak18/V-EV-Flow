from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .common import StrictModel
from .enums import DataType, Scenario


class Station(StrictModel):
    station_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    n_ports: int = Field(ge=1)
    power_kw: float = Field(gt=0)
    connector_types: list[str] = Field(min_length=1)
    network: str = Field(min_length=1)
    station_type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    assumptions: list[str]


class StationStatus(StrictModel):
    station_id: str = Field(min_length=1)
    ts: datetime
    ports_free: int = Field(ge=0)
    ports_busy: int = Field(ge=0)
    ports_broken: int = Field(ge=0)
    n_ports: int = Field(ge=1)
    scenario: Scenario

    @field_validator("ts")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("ts must be timezone-aware")
        return value

    @model_validator(mode="after")
    def conserve_ports(self) -> "StationStatus":
        if self.ports_free + self.ports_busy + self.ports_broken != self.n_ports:
            raise ValueError("port counts must sum to n_ports")
        return self


class StationListResponse(StrictModel):
    stations: tuple[Station, ...]
    data_type: DataType
    source_notes: list[str]
