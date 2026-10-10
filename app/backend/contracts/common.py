from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base for public DTOs: payloads cannot silently gain unknown fields."""

    model_config = ConfigDict(extra="forbid")


class Coordinate(StrictModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
