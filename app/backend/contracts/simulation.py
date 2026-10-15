from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .common import StrictModel
from .enums import DataType, Scenario, Strategy
from .recommendation import Vehicle, _aware

FixtureHash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


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

    @model_validator(mode="after")
    def ordered_window(self) -> "ScenarioConfig":
        if self.end < self.start:
            raise ValueError("end must be at or after start")
        return self


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

    @model_validator(mode="after")
    def failures_fit_population(self) -> "SimulationMetrics":
        if self.failed_count > self.vehicle_count:
            raise ValueError("failed_count cannot exceed vehicle_count")
        return self


class BackgroundArrival(StrictModel):
    station_id: str = Field(min_length=1)
    ts: datetime
    vehicle_id: str = Field(min_length=1)

    _ts_aware = field_validator("ts")(classmethod(lambda cls, v: _aware(v)))


class PortEvent(StrictModel):
    station_id: str = Field(min_length=1)
    ts: datetime
    ports_delta: int

    _ts_aware = field_validator("ts")(classmethod(lambda cls, v: _aware(v)))


class SimulationResult(StrictModel):
    scenario: Scenario
    seed: int
    strategy: Strategy
    model_version: str = Field(min_length=1)
    metrics: SimulationMetrics
    fixture_hash: FixtureHash
    contract_version: str = "0.1.0"


class ResetRequest(StrictModel):
    contract_version: str = "0.1.0"


class ResetResponse(StrictModel):
    reset: bool
    contract_version: str = "0.1.0"


class FixtureBundle(StrictModel):
    vehicles: tuple[Vehicle, ...]
    background_arrivals: tuple[BackgroundArrival, ...] = ()
    service_durations: tuple[float, ...] = ()
    port_events: tuple[PortEvent, ...] = ()
    scenario: Scenario
    seed: int


class DataManifest(StrictModel):
    fixture_hash: FixtureHash
    contract_version: str = "0.1.0"
    data_version: str = Field(min_length=1)
    scenario: Scenario
    seed: int
    counts: dict[str, int]
    generated_at: datetime
    data_type: DataType

    _generated_aware = field_validator("generated_at")(classmethod(lambda cls, v: _aware(v)))


class AddPortsChange(StrictModel):
    kind: Literal["add_ports"]
    station_id: str = Field(min_length=1)
    ports: int = Field(default=2, ge=1, le=20, strict=True)


class ShiftDeparturesChange(StrictModel):
    kind: Literal["shift_departures"]
    fraction: float = Field(default=0.2, gt=0, le=1, allow_inf_nan=False, strict=True)
    target_hour: int = Field(default=21, ge=20, le=21, strict=True)


WhatIfChange = Annotated[AddPortsChange | ShiftDeparturesChange, Field(discriminator="kind")]


class WhatIfRequest(SimulationRequest):
    seed: int = Field(ge=0, strict=True)
    vehicle_count: int = Field(gt=0, strict=True)
    change: WhatIfChange

    @model_validator(mode="after")
    def shift_moves_a_vehicle(self) -> "WhatIfRequest":
        if self.contract_version != "0.1.0":
            raise ValueError("unsupported what-if contract version")
        if (
            isinstance(self.change, ShiftDeparturesChange)
            and int(self.vehicle_count * self.change.fraction) < 1
        ):
            raise ValueError("population/fraction must shift at least one vehicle")
        return self


class WhatIfResult(StrictModel):
    before: SimulationResult
    after: SimulationResult
    change: WhatIfChange
    before_config_hash: FixtureHash
    after_config_hash: FixtureHash
    shifted_vehicle_count: int = Field(ge=0)
    data_type: Literal[DataType.SIMULATED] = DataType.SIMULATED
    assumptions: tuple[str, ...] = Field(min_length=1)
    prediction_mode: Literal["capacity_retrained"] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    capacity_model_version: str | None = Field(default=None, exclude_if=lambda value: value is None)
    capacity_history_hash: FixtureHash | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    contract_version: Literal["0.1.0"] = "0.1.0"

    @model_validator(mode="after")
    def fair_pair(self) -> "WhatIfResult":
        if self.before.contract_version != self.contract_version:
            raise ValueError("what-if nested result contract version mismatch")
        if self.before_config_hash == self.after_config_hash:
            raise ValueError(
                "before and after configurations must identify the counterfactual change"
            )
        if self.prediction_mode == "capacity_retrained":
            if (
                not isinstance(self.change, AddPortsChange)
                or self.capacity_model_version != self.after.model_version
                or not self.capacity_history_hash
            ):
                raise ValueError("retrained capacity requires matching model and history evidence")
        elif (
            self.before.model_version != self.after.model_version
            or self.capacity_model_version is not None
            or self.capacity_history_hash is not None
        ):
            raise ValueError("what-if model mismatch without explicit capacity retraining")
        for field in (
            "scenario",
            "seed",
            "strategy",
            "fixture_hash",
            "contract_version",
        ):
            if getattr(self.before, field) != getattr(self.after, field):
                raise ValueError("what-if must preserve scenario, seed, strategy and event fixture")
        if self.before.metrics.vehicle_count != self.after.metrics.vehicle_count:
            raise ValueError("what-if must preserve the population denominator")
        if self.shifted_vehicle_count > self.before.metrics.vehicle_count:
            raise ValueError("shifted count exceeds vehicle population")
        return self
