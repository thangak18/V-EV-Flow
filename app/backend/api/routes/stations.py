from fastapi import APIRouter, Depends

from app.backend.api.dependencies import AppContainer, get_container
from app.backend.contracts.enums import DataType
from app.backend.contracts.stations import StationListResponse

router = APIRouter()


@router.get("/stations", response_model=StationListResponse, operation_id="listStations")
def list_stations(container: AppContainer = Depends(get_container)) -> StationListResponse:
    data_type = DataType.SIMULATED if container.settings.data_backend == "file" else DataType.MOCK
    return StationListResponse(
        stations=container.stations.list_stations(),
        data_type=data_type,
        source_notes=[
            "Configured station repository; source metadata on each station describes assumptions."
        ],
    )
