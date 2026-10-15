from datetime import datetime, timedelta
from math import isclose

from pydantic import Field, field_validator, model_validator

from .common import Coordinate, StrictModel
from .enums import DataType, Scenario
from .explanations import ModelExplanation
from .prediction import _aware
from .stations import StationStatus


class Vehicle(StrictModel):
    soc_pct: float = Field(ge=0, le=100)
    battery_kwh: float = Field(gt=0)
    consumption_kwh_per_km: float = Field(gt=0)
    connector_type: str = Field(min_length=1)


class RecommendationRequest(StrictModel):
    request_id: str = Field(min_length=1)
    origin: Coordinate
    destination: Coordinate
    observed_at: datetime
    depart_time: datetime
    scenario: Scenario
    vehicle: Vehicle

    _observed_aware = field_validator("observed_at")(classmethod(lambda cls, v: _aware(v)))
    _depart_aware = field_validator("depart_time")(classmethod(lambda cls, v: _aware(v)))


class PlanLeg(StrictModel):
    station_id: str = Field(min_length=1)
    eta: datetime
    distance_km: float = Field(ge=0)
    detour_km: float = Field(ge=0)
    arrival_soc_pct: float = Field(ge=0, le=100)
    p_available: float = Field(ge=0, le=1)
    explanation: ModelExplanation | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    _eta_aware = field_validator("eta")(classmethod(lambda cls, v: _aware(v)))

    @model_validator(mode="after")
    def explanation_matches_probability(self) -> "PlanLeg":
        if self.explanation is not None and not isclose(
            self.explanation.calibrated_probability, self.p_available, rel_tol=1e-8, abs_tol=1e-8
        ):
            raise ValueError("plan explanation probability must match its prediction")
        return self


class Plan(PlanLeg):
    pass


class TimeShiftEstimate(StrictModel):
    minutes: int = Field(gt=0, le=60, multiple_of=5)
    station_id: str = Field(min_length=1)
    depart_time: datetime
    eta: datetime
    p_available: float = Field(ge=0, le=1, allow_inf_nan=False)
    improvement: float = Field(gt=0, le=1, allow_inf_nan=False)
    assumptions: tuple[str, ...] = Field(min_length=1)

    _depart_aware = field_validator("depart_time")(classmethod(lambda cls, v: _aware(v)))
    _eta_aware = field_validator("eta")(classmethod(lambda cls, v: _aware(v)))


class RecommendationResult(StrictModel):
    request_id: str = Field(min_length=1)
    primary: Plan | None
    backup: Plan | None
    plan_p: float | None = Field(default=None, ge=0, le=1)
    plan_p_assumption: str | None = None
    reasons: list[str]
    time_shift: int | None = Field(default=None, gt=0, le=60, multiple_of=5)
    time_shift_evaluated: bool | None = Field(default=None, exclude_if=lambda value: value is None)
    time_shift_estimate: TimeShiftEstimate | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    model_version: str = Field(min_length=1)
    allocation_method: str = Field(min_length=1)
    data_type: DataType
    contract_version: str = "0.1.0"

    @model_validator(mode="after")
    def time_shift_matches_current_plan(self) -> "RecommendationResult":
        estimate = self.time_shift_estimate
        if estimate is not None:
            if (
                self.primary is None
                or estimate.minutes != self.time_shift
                or estimate.station_id != self.primary.station_id
            ):
                raise ValueError("time-shift estimate must refer to the primary plan and delay")
            if estimate.eta != self.primary.eta + timedelta(minutes=estimate.minutes):
                raise ValueError("time-shift ETA must preserve the original travel duration")
            if not isclose(
                estimate.p_available - self.primary.p_available, estimate.improvement, abs_tol=1e-8
            ):
                raise ValueError("time-shift improvement must match the probability difference")
        return self


class PressureStation(StrictModel):
    station_id: str = Field(min_length=1)
    p_available: float = Field(ge=0, le=1)
    pressure_score: float = Field(ge=0, le=1)
    data_type: DataType


class PressureResponse(StrictModel):
    time: datetime
    scenario: Scenario
    stations: tuple[PressureStation, ...]
    contract_version: str = "0.1.0"

    _time_aware = field_validator("time")(classmethod(lambda cls, v: _aware(v)))


class RouteRequest(StrictModel):
    origin: Coordinate
    destination: Coordinate
    depart_time: datetime
    vehicle: Vehicle | None = None

    _depart_aware = field_validator("depart_time")(classmethod(lambda cls, v: _aware(v)))


class RouteResult(StrictModel):
    distance_km: float = Field(ge=0)
    duration_minutes: float = Field(ge=0)
    geometry: tuple[Coordinate, ...] | None = None
    source: str = Field(min_length=1)


class StatusWindow(StrictModel):
    station_id: str = Field(min_length=1)
    observed_at: datetime
    lags: tuple[int, ...] = Field(min_length=1)
    statuses: tuple[StationStatus, ...]

    @field_validator("lags")
    @classmethod
    def valid_lags(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(lag < 0 for lag in value):
            raise ValueError("lags must be nonnegative")
        return value

    _observed_aware = field_validator("observed_at")(classmethod(lambda cls, v: _aware(v)))


class FeasibleCandidate(StrictModel):
    station_id: str = Field(min_length=1)
    distance_km: float = Field(ge=0)
    detour_km: float = Field(ge=0)
    arrival_soc_pct: float = Field(ge=0, le=100)
    p_available: float = Field(ge=0, le=1)
    eta: datetime

    _eta_aware = field_validator("eta")(classmethod(lambda cls, v: _aware(v)))


class RankedCandidate(FeasibleCandidate):
    rank: int = Field(ge=1)
    score: float


class RankedPlan(StrictModel):
    primary: RankedCandidate | None
    backup: RankedCandidate | None
    plan_p: float | None = Field(default=None, ge=0, le=1)
    reasons: list[str]


class AllocationContext(StrictModel):
    request: RecommendationRequest
    candidates: tuple[FeasibleCandidate, ...]


RecommendRequest = RecommendationRequest
RecommendResponse = RecommendationResult
PressureResult = PressureResponse
