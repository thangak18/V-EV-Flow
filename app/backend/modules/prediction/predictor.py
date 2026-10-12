"""Runtime calibrated ETA prediction using an immutable trained artifact.

The StatusRepository must supply a current snapshot (lag 0) and any available
15/30/60-minute snapshots for the requested station/scenario. The fitted
feature imputer fills missing *past* windows; future statuses are never read.
"""

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from app.backend.contracts.enums import DataType
from app.backend.contracts.ports import StationRepository, StatusRepository
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import StatusWindow
from app.backend.contracts.stations import Station, StationStatus
from app.backend.modules.prediction.artifacts import ModelManifest
from app.backend.modules.prediction.dataset import validate_status_frame
from app.backend.modules.prediction.features import LAG_MINUTES
from app.backend.modules.prediction.labels import LABEL_COLUMNS
from app.backend.modules.prediction.training import TrainedPipeline


@dataclass(frozen=True)
class ModelPredictor:
    """Implementation of the shared Predictor protocol; no API route logic."""

    pipeline: TrainedPipeline
    manifest: ModelManifest
    status_repository: StatusRepository
    station_repository: StationRepository
    status_data_type: DataType = DataType.MOCK

    def predict(self, request: PredictRequest) -> PredictionResult:
        if not isinstance(request, PredictRequest):
            raise TypeError("request must be a PredictRequest")
        horizon = self._validate_horizon(request)
        station = self.station_repository.get_station(request.station_id)
        if request.connector_type not in station.connector_types:
            raise ValueError("requested connector is incompatible with station")
        if len(set(station.connector_types)) != 1:
            raise ValueError(
                "mixed connector stations need connector-specific status; "
                "aggregate ports are unsafe"
            )

        window = self.status_repository.window(
            request.station_id, request.observed_at, lags=(0, *LAG_MINUTES)
        )
        current, frame = self._frame_from_window(window, request, station)
        # The target is a sentinel required by the training feature-builder's
        # labeled-frame API. It is NEVER used in feature construction/inference.
        labels = pd.DataFrame(
            [
                {
                    "station_id": request.station_id,
                    "scenario": request.scenario.value,
                    "observed_at": request.observed_at,
                    "eta": request.eta,
                    "horizon_minutes": horizon,
                    "target_available": 0,
                }
            ],
            columns=list(LABEL_COLUMNS),
        )
        features = self.pipeline.feature_builder.build(frame, labels).X
        self._verify_station_metadata(features, station)
        probability = float(self.pipeline.predict_proba(features)[0, 1])

        trained_type = DataType(self.pipeline.data_type)
        result_type = trained_type if trained_type == self.status_data_type else DataType.MIXED
        return PredictionResult(
            station_id=request.station_id,
            eta=request.eta,
            p_available=probability,
            reasons=[
                f"At observation: {current.ports_free} of {station.n_ports} ports free.",
                f"Calibrated {horizon}-minute ETA prediction (rule-based context, not SHAP).",
                f"Training data: {trained_type.value}; "
                f"status source: {self.status_data_type.value}; "
                f"model source: {self.manifest.source}.",
            ],
            explanation_method="rule",
            model_version=self.manifest.model_version,
            data_type=result_type,
            contract_version=self.manifest.contract_version,
        )

    def _validate_horizon(self, request: PredictRequest) -> int:
        observed = request.observed_at
        if (
            observed.utcoffset() != timedelta(hours=7)
            or request.eta.utcoffset() != timedelta(hours=7)
            or observed.minute % 5
            or observed.second
            or observed.microsecond
        ):
            raise ValueError(
                "observed_at and ETA must use +07:00; observed_at must align to five-minute buckets"
            )
        seconds = (request.eta - observed).total_seconds()
        maximum = self.pipeline.split_metadata.max_horizon_minutes
        if seconds <= 0 or seconds % 300 != 0 or seconds > maximum * 60:
            raise ValueError(
                f"ETA horizon must be a positive five-minute multiple <= {maximum} minutes"
            )
        return int(seconds // 60)

    @staticmethod
    def _frame_from_window(
        window: StatusWindow, request: PredictRequest, station: Station
    ) -> tuple[StationStatus, pd.DataFrame]:
        if window.station_id != request.station_id or window.observed_at != request.observed_at:
            raise ValueError("status window station/observed_at mismatch")
        expected = {request.observed_at - timedelta(minutes=lag) for lag in (0, *LAG_MINUTES)}
        for snapshot in window.statuses:
            if snapshot.station_id != request.station_id:
                raise ValueError("status window station mismatch")
            if snapshot.scenario != request.scenario:
                raise ValueError("status window scenario mismatch")
            if snapshot.ts > request.observed_at:
                raise ValueError("future status snapshot after observed_at is forbidden")
            if snapshot.ts not in expected:
                raise ValueError("status window includes an unrequested timestamp")
            if snapshot.n_ports != station.n_ports:
                raise ValueError("status window station capacity mismatch")
        current = [item for item in window.statuses if item.ts == request.observed_at]
        if len(current) != 1:
            raise ValueError("exactly one current status snapshot at observed_at is required")
        records = [
            {
                "station_id": item.station_id,
                "ts": item.ts,
                "ports_free": item.ports_free,
                "ports_busy": item.ports_busy,
                "ports_broken": item.ports_broken,
                "scenario": item.scenario.value,
            }
            for item in window.statuses
        ]
        frame = validate_status_frame(pd.DataFrame(records), [station])
        return current[0], frame

    @staticmethod
    def _verify_station_metadata(features: pd.DataFrame, station: Station) -> None:
        """Avoid using stale training metadata if the source changed capacity/type."""
        station_type = station.station_type.lower()
        expected = {
            "n_ports": float(station.n_ports),
            "power_kw": float(station.power_kw),
            "station_type_urban": float(station_type == "urban"),
            "station_type_highway": float(station_type == "highway"),
            "station_type_other": float(station_type not in ("urban", "highway")),
        }
        if any(float(features.iloc[0][name]) != value for name, value in expected.items()):
            raise ValueError("station metadata differs from trained features; retrain model")
