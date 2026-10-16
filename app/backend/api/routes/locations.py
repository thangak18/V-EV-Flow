"""Search suggestions and resolve coordinates through server-side Goong."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.backend.api.dependencies import AppContainer, get_container
from app.backend.api.errors import FeatureNotReadyError
from app.backend.contracts.errors import ErrorResponse
from app.backend.contracts.locations import PlaceLocation, PlaceSuggestions
from app.backend.contracts.recommendation import RouteRequest, RouteResult

router = APIRouter()


@router.get(
    "/places/search",
    response_model=PlaceSuggestions,
    operation_id="searchPlaces",
    responses={503: {"model": ErrorResponse}},
)
async def search_places(
    q: str = Query(min_length=2, max_length=200, pattern=r".*\S.*"),
    session: UUID | None = None,
    container: AppContainer = Depends(get_container),
) -> PlaceSuggestions:
    if container.places is None:
        raise FeatureNotReadyError("Goong place search is not configured")
    return await container.places.search(q, str(session) if session else None)


@router.get(
    "/places/detail",
    response_model=PlaceLocation,
    operation_id="resolvePlace",
    responses={503: {"model": ErrorResponse}},
)
async def resolve_place(
    place_id: str = Query(min_length=1, max_length=1024),
    session: UUID | None = None,
    container: AppContainer = Depends(get_container),
) -> PlaceLocation:
    if container.places is None:
        raise FeatureNotReadyError("Goong place search is not configured")
    return await container.places.detail(place_id, str(session) if session else None)


@router.post(
    "/routes",
    response_model=tuple[RouteResult, ...],
    operation_id="mapRoutes",
    responses={503: {"model": ErrorResponse}},
)
async def map_routes(
    request: RouteRequest,
    container: AppContainer = Depends(get_container),
) -> tuple[RouteResult, ...]:
    """Read-only road geometry; never records recommendations or allocations."""
    return await container.routes.get_routes(request)
