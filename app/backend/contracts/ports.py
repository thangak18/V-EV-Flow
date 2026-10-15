from datetime import datetime
from typing import Protocol, runtime_checkable

from .prediction import PredictionResult, PredictRequest
from .recommendation import (
    AllocationContext,
    RankedPlan,
    RouteRequest,
    RouteResult,
    StatusWindow,
)
from .simulation import SimulationRequest, SimulationResult, WhatIfRequest, WhatIfResult
from .stations import Station


@runtime_checkable
class StationRepository(Protocol):
    def list_stations(self) -> tuple[Station, ...]: ...
    def get_station(self, station_id: str) -> Station: ...


@runtime_checkable
class StatusRepository(Protocol):
    def window(
        self,
        station_id: str,
        observed_at: datetime,
        lags: tuple[int, ...] = (15, 30, 60),
    ) -> StatusWindow: ...


@runtime_checkable
class RouteProvider(Protocol):
    async def get_routes(self, request: RouteRequest) -> tuple[RouteResult, ...]: ...


@runtime_checkable
class Predictor(Protocol):
    def predict(self, request: PredictRequest) -> PredictionResult: ...


@runtime_checkable
class AllocationStrategy(Protocol):
    def select(self, context: AllocationContext) -> RankedPlan: ...


@runtime_checkable
class SimulationRunner(Protocol):
    def run(self, request: SimulationRequest, strategy: AllocationStrategy) -> SimulationResult: ...


@runtime_checkable
class WhatIfRunner(Protocol):
    def run_whatif(self, request: WhatIfRequest) -> WhatIfResult: ...
