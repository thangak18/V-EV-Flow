from fastapi import APIRouter, Depends

from app.backend.api.dependencies import AppContainer, get_container
from app.backend.contracts.enums import DataType
from app.backend.contracts.stations import StationListResponse

router = APIRouter()


@router.get("/stations", response_model=StationListResponse, operation_id="listStations")
def list_stations(container: AppContainer = Depends(get_container)) -> StationListResponse:
    return StationListResponse(
        stations=container.stations.list_stations(),
        data_type=DataType.MOCK,
        source_notes=[
            "Phase 0 synthetic station fixture; locations and capacities are assumptions."
        ],
    )
