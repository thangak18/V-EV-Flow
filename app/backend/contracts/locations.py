"""Public place-search contracts, with provider credentials kept server-side."""

from pydantic import Field

from .common import Coordinate, StrictModel


class PlaceSuggestion(StrictModel):
    place_id: str = Field(min_length=1, max_length=1024)
    description: str = Field(min_length=1, max_length=1024)


class PlaceSuggestions(StrictModel):
    predictions: tuple[PlaceSuggestion, ...]
    provider: str = "goong"


class PlaceLocation(Coordinate):
    place_id: str = Field(min_length=1, max_length=1024)
    label: str = Field(min_length=1, max_length=1024)
    provider: str = "goong"
