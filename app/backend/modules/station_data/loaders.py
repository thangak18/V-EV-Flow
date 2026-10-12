"""Load and validate committed station and scenario fixtures.

The shared ``ScenarioConfig`` contract only carries the window, seed, demand
multiplier and compliance rate. Simulation parameters (charging time, fault
and repair rates, demand coefficients) live in the module-internal
``ScenarioSpec`` and are mapped to the contract through ``to_config``.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator, model_validator

from app.backend.contracts.common import StrictModel
from app.backend.contracts.enums import Scenario
from app.backend.contracts.simulation import ScenarioConfig
from app.backend.contracts.stations import Station

FIXTURE_DIR = Path(__file__).parent / "fixtures"
STATIONS_PATH = FIXTURE_DIR / "stations.json"
SCENARIOS_PATH = FIXTURE_DIR / "scenarios.yaml"

STEP_MINUTES = 5
_OFFSET = timedelta(hours=7)
_DAY_KEYS = frozenset({"weekday", "saturday", "sunday"})


class ScenarioSpec(StrictModel):
    """Full, validated simulation parameters for one scenario."""

    scenario: Scenario
    seed: int
    step_minutes: int
    start: datetime
    end: datetime
    arrival_multiplier: float = Field(gt=0)
    holiday_multiplier: float = Field(gt=0)
    hour_coefficients: dict[int, float]
    day_coefficients: dict[str, float]
    station_type_coefficients: dict[str, float]
    charging_minutes: tuple[float, float]
    fault_probability: float = Field(ge=0, le=1)
    repair_probability: float = Field(ge=0, le=1)
    suggestion_compliance: float = Field(ge=0, le=1)
    history_days: int = Field(ge=1)
    source: str = Field(min_length=1)
    assumptions: list[str] = Field(min_length=1)

    @field_validator("start", "end")
    @classmethod
    def require_utc_plus_7(cls, value: datetime) -> datetime:
        if value.utcoffset() != _OFFSET:
            raise ValueError("timestamps must carry +07:00")
        return value

    @field_validator("hour_coefficients")
    @classmethod
    def validate_hours(cls, value: dict[int, float]) -> dict[int, float]:
        if 0 not in value or any(not 0 <= hour <= 23 for hour in value):
            raise ValueError("by_hour needs key '00' and hours within 00-23")
        if any(coef < 0 for coef in value.values()):
            raise ValueError("coefficients must be non-negative")
        return value

    @field_validator("day_coefficients")
    @classmethod
    def validate_days(cls, value: dict[str, float]) -> dict[str, float]:
        if set(value) != _DAY_KEYS:
            raise ValueError(f"by_day keys must be {sorted(_DAY_KEYS)}")
        if any(coef < 0 for coef in value.values()):
            raise ValueError("coefficients must be non-negative")
        return value

    @field_validator("station_type_coefficients")
    @classmethod
    def validate_station_types(cls, value: dict[str, float]) -> dict[str, float]:
        if not value or any(coef < 0 for coef in value.values()):
            raise ValueError("by_station_type must be non-empty and non-negative")
        return value

    @field_validator("charging_minutes")
    @classmethod
    def validate_charging(cls, value: tuple[float, float]) -> tuple[float, float]:
        if not 0 < value[0] <= value[1]:
            raise ValueError("charging_minutes must satisfy 0 < min <= max")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> "ScenarioSpec":
        if self.step_minutes != STEP_MINUTES:
            raise ValueError(f"step_minutes must be {STEP_MINUTES}")
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self

    def history_spec(self, days: int | None = None, end: datetime | None = None) -> "ScenarioSpec":
        """Same scenario, window of ``days`` days ending at ``end``.

        ``days`` defaults to ``history_days``; ``end`` defaults to the scenario
        end. Passing one common ``end`` for every scenario puts them on a shared
        calendar window, which global temporal train/calibration/test splits
        need so each scenario appears in every partition.
        """
        count = self.history_days if days is None else days
        if count < 1:
            raise ValueError("history days must be at least 1")
        last = self.end if end is None else end
        if last.utcoffset() != _OFFSET:
            raise ValueError("history end must carry +07:00")
        start = last + timedelta(minutes=self.step_minutes) - timedelta(days=count)
        return self.model_copy(update={"start": start, "end": last, "history_days": count})

    def to_config(self) -> ScenarioConfig:
        return ScenarioConfig(
            scenario=self.scenario,
            seed=self.seed,
            start=self.start,
            end=self.end,
            step_minutes=self.step_minutes,
            demand_multiplier=self.arrival_multiplier,
            compliance_rate=self.suggestion_compliance,
        )


def load_stations(path: Path = STATIONS_PATH) -> tuple[Station, ...]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    stations = tuple(Station.model_validate(row) for row in rows)
    if len({item.station_id for item in stations}) != len(stations):
        raise ValueError("station_id values must be unique")
    return stations


def _spec_from_row(name: str, row: dict[str, Any], seed: int, step: int) -> ScenarioSpec:
    coefficients = row["demand_arrival_coefficients"]
    return ScenarioSpec(
        scenario=Scenario(name),
        seed=seed,
        step_minutes=step,
        start=row["start"],
        end=row["end"],
        arrival_multiplier=row["arrival_multiplier"],
        holiday_multiplier=row["holiday_multiplier"],
        hour_coefficients={int(hour): coef for hour, coef in coefficients["by_hour"].items()},
        day_coefficients=coefficients["by_day"],
        station_type_coefficients=coefficients["by_station_type"],
        charging_minutes=tuple(row["charging_minutes"]),
        fault_probability=row["fault_probability"],
        repair_probability=row["repair_probability"],
        suggestion_compliance=row["suggestion_compliance"],
        history_days=row.get("history_days", 14),
        source=row["source"],
        assumptions=row["assumptions"],
    )


def load_scenario_specs(path: Path = SCENARIOS_PATH) -> dict[Scenario, ScenarioSpec]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    seed, step = payload["seed"], payload["step_minutes"]
    specs = {
        Scenario(name): _spec_from_row(name, row, seed, step)
        for name, row in payload["scenarios"].items()
    }
    if set(specs) != set(Scenario):
        raise ValueError("scenarios.yaml must define every Scenario exactly once")
    return specs


def load_scenarios(path: Path = SCENARIOS_PATH) -> dict[Scenario, ScenarioConfig]:
    return {name: spec.to_config() for name, spec in load_scenario_specs(path).items()}
