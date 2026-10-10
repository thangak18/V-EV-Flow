from datetime import datetime

from pydantic import Field, field_validator

from .common import StrictModel
from .enums import DataType, Scenario, Strategy
from .recommendation import Vehicle, _aware


class ScenarioConfig(StrictModel):
    scenario: Scenario
    seed: int
    start: datetime
    end: datetime
    step_minutes: int = Field(gt=0)
    demand_multiplier: float = Field(gt=0)
    compliance_rate: float = Field(ge=0, le=1)

    _start_aware = field_validator("start")(classmethod(lambda cls, v: _aware(v)))
    _end_aware = field_validator("end")(classmethod(lambda cls, v: _aware(v)))


class SimulationRequest(StrictModel):
    scenario: Scenario
    seed: int
    vehicle_count: int = Field(gt=0)
    strategy: Strategy
    contract_version: str = "0.1.0"


class SimulationMetrics(StrictModel):
    success_rate: float = Field(ge=0, le=1)
    mean_detour_km: float = Field(ge=0)
    mean_wait_minutes: float = Field(ge=0)
    failed_count: int = Field(ge=0)
    vehicle_count: int = Field(ge=0)


class SimulationResult(StrictModel):
    scenario: Scenario
    seed: int
    strategy: Strategy
    model_version: str = Field(min_length=1)
    metrics: SimulationMetrics
    fixture_hash: str = Field(min_length=1)
    contract_version: str = "0.1.0"


class ResetRequest(StrictModel):
    contract_version: str = "0.1.0"


class ResetResponse(StrictModel):
    reset: bool
    contract_version: str = "0.1.0"


class FixtureBundle(StrictModel):
    vehicles: tuple[Vehicle, ...]
    background_arrivals: tuple[object, ...] = ()
    service_durations: tuple[float, ...] = ()
    port_events: tuple[object, ...] = ()
    scenario: Scenario
    seed: int


class DataManifest(StrictModel):
    fixture_hash: str = Field(min_length=1)
    contract_version: str = "0.1.0"
    data_version: str = Field(min_length=1)
    scenario: Scenario
    seed: int
    counts: dict[str, int]
    generated_at: datetime
    data_type: DataType

    _generated_aware = field_validator("generated_at")(classmethod(lambda cls, v: _aware(v)))

