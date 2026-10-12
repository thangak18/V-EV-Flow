"""Stable prediction-module entry point for the API/infrastructure owner."""

from pathlib import Path

from app.backend.contracts.enums import DataType
from app.backend.contracts.ports import Predictor, StationRepository, StatusRepository
from app.backend.modules.prediction.artifacts import (
    DEFAULT_CONTRACT_VERSION,
    load_pipeline,
    read_manifest,
)
from app.backend.modules.prediction.predictor import ModelPredictor


def load_predictor(
    model_dir: Path | str,
    status_repository: StatusRepository,
    station_repository: StationRepository,
    *,
    status_data_type: DataType = DataType.MOCK,
) -> Predictor:
    """Load a trusted artifact and bind existing shared repositories.

    StatusWindow lacks provenance in contract v0: callers must explicitly
    identify any non-mock status source using ``status_data_type``.
    """
    manifest = read_manifest(model_dir)
    pipeline = load_pipeline(model_dir, expected_contract_version=DEFAULT_CONTRACT_VERSION)
    return ModelPredictor(
        pipeline=pipeline,
        manifest=manifest,
        status_repository=status_repository,
        station_repository=station_repository,
        status_data_type=status_data_type,
    )
