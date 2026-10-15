"""Bounded Goong Places V2 proxy. Never expose provider error URLs or credentials."""

from collections import OrderedDict
from time import monotonic

import httpx
from pydantic import ValidationError

from app.backend.contracts.errors import RouteUnavailableError
from app.backend.contracts.locations import PlaceLocation, PlaceSuggestion, PlaceSuggestions


class GoongPlaces:
    def __init__(self, key: str, client: httpx.AsyncClient) -> None:
        self.key = key
        self.client = client
        self.cache: OrderedDict[str, tuple[float, PlaceLocation]] = OrderedDict()

    async def _get(self, path: str, params: dict[str, str]) -> dict:
        try:
            response = await self.client.get(
                "https://rsapi.goong.io/v2/place/" + path,
                params={**params, "api_key": self.key},
                timeout=httpx.Timeout(8, connect=2),
            )
            response.raise_for_status()
            value = response.json()
            if (
                not isinstance(value, dict)
                or value.get("error")
                or value.get("status") not in (None, "OK", "ZERO_RESULTS")
            ):
                raise ValueError("invalid provider response")
            return value
        except (httpx.HTTPError, ValueError, TypeError):
            raise RouteUnavailableError("Goong place search is unavailable") from None

    async def search(self, query: str, session: str | None) -> PlaceSuggestions:
        params = {"input": query.strip(), "limit": "5"}
        if session:
            params["sessiontoken"] = session
        value = await self._get("autocomplete", params)
        try:
            rows = value["predictions"]
            if not isinstance(rows, list):
                raise ValueError("predictions must be a list")
            return PlaceSuggestions(
                predictions=tuple(
                    PlaceSuggestion(place_id=row["place_id"], description=row["description"])
                    for row in rows[:5]
                )
            )
        except (KeyError, TypeError, ValueError, ValidationError):
            raise RouteUnavailableError("Goong returned invalid place suggestions") from None

    async def detail(self, place_id: str, session: str | None) -> PlaceLocation:
        cached = self.cache.get(place_id)
        if cached and cached[0] > monotonic():
            self.cache.move_to_end(place_id)
            return cached[1].model_copy(deep=True)
        params = {"place_id": place_id}
        if session:
            params["sessiontoken"] = session
        value = await self._get("detail", params)
        try:
            row = value["result"]
            if row["place_id"] != place_id:
                raise ValueError("place identity mismatch")
            location = PlaceLocation(
                place_id=place_id,
                label=row.get("formatted_address") or row["name"],
                **row["geometry"]["location"],
            )
        except (KeyError, TypeError, ValueError, ValidationError):
            raise RouteUnavailableError("Goong returned invalid place coordinates") from None
        self.cache[place_id] = (monotonic() + 3600, location)
        while len(self.cache) > 256:
            self.cache.popitem(last=False)
        return location.model_copy(deep=True)
