"""Validated settings for selecting replaceable backend adapters."""

from datetime import datetime, timedelta
from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BackendKind = Literal["mock", "file", "real"]
PredictorKind = Literal["fake", "model"]
RouteKind = Literal["fake", "goong"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and defaults."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_backend: BackendKind = "mock"
    partner_source: str | None = None
    partner_ingest_token: str | None = Field(default=None, repr=False)
    partner_history_path: Path = Path(".cache/partner-history.sqlite3")
    live_max_age_seconds: int = Field(default=600, ge=300, le=3600)
    replay_observed_at: datetime | None = None
    predictor_backend: PredictorKind = "fake"
    route_backend: RouteKind = "fake"
    places_backend: Literal["disabled", "goong"] = "disabled"
    prediction_explanations: bool = False
    time_shift_suggestions: bool = False
    simulation_backend: Literal["fake", "stateful"] = "fake"
    capacity_models_dir: Path | None = None
    simulation_scenarios_path: Path = Path(
        "app/backend/modules/station_data/fixtures/scenarios.yaml"
    )
    data_dir: Path = Path("app/backend/modules/station_data")
    model_dir: Path = Path("app/backend/modules/prediction/artifacts")
    demo_seed: int = 42
    min_arrival_soc_pct: float = 10.0
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    goong_rest_api_key: str | None = Field(default=None, repr=False)
    goong_cache_dir: Path = Path(".cache/goong-routes")
    goong_cache_ttl_seconds: int = 3600
    allocation_backend: Literal["memory", "sqlite"] = "memory"
    allocation_db_path: Path = Path(".cache/allocation.sqlite3")
    virtual_load_receipt_ttl_seconds: int = 1800
    assumed_charge_duration_minutes: float = 60.0
    expected_virtual_load: float = 1.0
    fake_prediction_horizon_minutes: int = 60

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_selected_backends(self) -> "Settings":
        replay = self.replay_observed_at
        if replay is not None and (
            replay.utcoffset() != timedelta(hours=7)
            or replay.minute % 5
            or replay.second
            or replay.microsecond
        ):
            raise ValueError("REPLAY_OBSERVED_AT must be a +07:00 five-minute bucket")
        if self.predictor_backend == "model" and self.data_backend not in ("file", "real"):
            raise ValueError("model prediction requires DATA_BACKEND=file or real")
        if self.data_backend == "real" and (
            not self.partner_source
            or not self.partner_ingest_token
            or len(self.partner_ingest_token.strip()) < 32
        ):
            raise ValueError("real data requires partner source and ingestion token (32+ chars)")
        if self.simulation_backend == "stateful" and (
            self.data_backend != "file" or self.predictor_backend != "model"
        ):
            raise ValueError("stateful simulation requires file data and model prediction")
        if (
            self.route_backend == "goong" or self.places_backend == "goong"
        ) and not self.goong_rest_api_key:
            raise ValueError("GOONG_REST_API_KEY is required for ROUTE_BACKEND=goong")
        if self.predictor_backend == "model" and not self.model_dir.exists():
            raise ValueError("MODEL_DIR must exist for PREDICTOR_BACKEND=model")
        if self.fake_prediction_horizon_minutes <= 0 or self.fake_prediction_horizon_minutes % 5:
            raise ValueError(
                "FAKE_PREDICTION_HORIZON_MINUTES must be a positive five-minute multiple"
            )
        if self.fake_prediction_horizon_minutes < 30:
            raise ValueError(
                "FAKE_PREDICTION_HORIZON_MINUTES must support the 30-minute pressure proxy"
            )
        if self.goong_cache_ttl_seconds <= 0 or self.virtual_load_receipt_ttl_seconds <= 0:
            raise ValueError("cache and receipt TTL values must be positive")
        if (
            not isfinite(self.assumed_charge_duration_minutes)
            or self.assumed_charge_duration_minutes <= 0
        ):
            raise ValueError("ASSUMED_CHARGE_DURATION_MINUTES must be finite and positive")
        from app.backend.modules.recommendation.allocation import MAX_RESERVATION_DURATION_MINUTES

        if self.assumed_charge_duration_minutes > MAX_RESERVATION_DURATION_MINUTES:
            raise ValueError("ASSUMED_CHARGE_DURATION_MINUTES exceeds the C6 reservation maximum")
        if not isfinite(self.expected_virtual_load) or self.expected_virtual_load < 0:
            raise ValueError("EXPECTED_VIRTUAL_LOAD must be finite and nonnegative")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached settings instance."""

    return Settings()
