"""Versioned LightGBM pipeline persistence with checked, atomic artifacts.

The JSON manifest is readable without loading pickle. Verify the schema,
contract version, feature order and SHA-256 *before* calling joblib.load.
Only load artifacts produced by a trusted source: SHA-256 detects accidental
changes but does not authenticate a maliciously replaced manifest and pickle.
"""

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.backend.modules.prediction.features import FEATURE_COLUMNS
from app.backend.modules.prediction.training import DataType, TrainedPipeline

MANIFEST_SCHEMA_VERSION = "1"
DEFAULT_CONTRACT_VERSION = "0.1.0"
MANIFEST_FILENAME = "manifest.json"
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_MODEL_FILENAME_PATTERN = re.compile(r"model-([0-9a-f]{64})\.joblib\Z")


class ModelManifest(BaseModel):
    """Reviewable source, model, feature and evaluation metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["1"]
    model_version: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    created_at: datetime
    model_file: str
    binary_sha256: str
    model_class: Literal["LGBMClassifier"]
    calibrator_class: Literal["IsotonicRegression", "LogisticRegression"]
    calibration_method: Literal["isotonic", "platt"]
    feature_columns: list[str]
    lag_fill_values: dict[str, float]
    training_config: dict[str, Any]
    split_metadata: dict[str, Any]
    calibration_brier: dict[str, float]
    test_metrics: dict[str, Any]
    sample_counts: dict[str, int]
    scenarios: list[str]
    seed: int | None
    data_type: DataType
    source: str = Field(min_length=1)
    data_version: str = Field(min_length=1)
    fixture_hash: str | None = None

    @model_validator(mode="after")
    def check_integrity_fields(self) -> "ModelManifest":
        match = _MODEL_FILENAME_PATTERN.fullmatch(self.model_file)
        if match is None or _HASH_PATTERN.fullmatch(self.binary_sha256) is None:
            raise ValueError("manifest model_file or binary_sha256 has an invalid SHA-256 format")
        if match.group(1) != self.binary_sha256:
            raise ValueError("manifest model_file hash does not match binary_sha256")
        if self.fixture_hash is not None and _HASH_PATTERN.fullmatch(self.fixture_hash) is None:
            raise ValueError("fixture_hash must be a lowercase SHA-256 hex digest")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("manifest created_at must be timezone-aware")
        if (self.calibration_method == "isotonic") != (
            self.calibrator_class == "IsotonicRegression"
        ):
            raise ValueError("manifest calibration_method and calibrator_class disagree")
        return self


def _json_value(value: Any) -> Any:
    """Turn dataclasses, numpy scalars and timestamps into stable JSON values."""
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _pipeline_metadata(pipeline: TrainedPipeline) -> dict[str, Any]:
    reports = _json_value(pipeline.test_metrics)
    # Old joblib reports predate Log Loss; retain their original metadata shape.
    for report in reports.values():
        if report.get("log_loss") is None:
            report.pop("log_loss", None)
    return {
        "model_class": type(pipeline.model).__name__,
        "calibrator_class": type(pipeline.calibrator).__name__,
        "calibration_method": pipeline.calibration_method,
        "feature_columns": list(pipeline.feature_columns),
        "lag_fill_values": pipeline.feature_builder.lag_fill_values,
        "training_config": _json_value(pipeline.config),
        "split_metadata": _json_value(pipeline.split_metadata),
        "calibration_brier": pipeline.calibration_brier.copy(),
        "test_metrics": reports,
        "sample_counts": pipeline.sample_counts.copy(),
        "scenarios": list(pipeline.scenarios),
        "seed": pipeline.seed,
        "data_type": pipeline.data_type,
        "source": pipeline.source,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_feature_order(columns: list[str]) -> None:
    if tuple(columns) != FEATURE_COLUMNS:
        raise ValueError("manifest feature columns/order incompatible with this prediction version")


def save_pipeline(
    pipeline: TrainedPipeline,
    directory: Path | str,
    *,
    contract_version: str = DEFAULT_CONTRACT_VERSION,
    data_version: str = "unspecified",
    fixture_hash: str | None = None,
) -> ModelManifest:
    """Atomically publish a versioned model and manifest within ``directory``.

    Binary names are content-addressed. Publishing the manifest last means
    interrupted replacements leave the previous version readable. The
    optional ``fixture_hash`` must be provided by the caller when a source
    fixture is available; absence is recorded as null, never fabricated.
    """
    if not isinstance(pipeline, TrainedPipeline):
        raise TypeError("pipeline must be a trained TrainedPipeline")
    _verify_feature_order(list(pipeline.feature_columns))
    if not isinstance(contract_version, str) or not contract_version.strip():
        raise ValueError("contract_version must be a nonempty string")
    if not isinstance(data_version, str) or not data_version.strip():
        raise ValueError("data_version must be a nonempty string")
    if fixture_hash is not None and (
        not isinstance(fixture_hash, str) or _HASH_PATTERN.fullmatch(fixture_hash) is None
    ):
        raise ValueError("fixture_hash must be a lowercase SHA-256 hex digest")

    metadata = _pipeline_metadata(pipeline)
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    # A compressed joblib dump is one binary file, so os.replace is atomic.
    with tempfile.NamedTemporaryFile(
        dir=folder, prefix=".model-", suffix=".joblib", delete=False
    ) as temp:
        temporary_model = Path(temp.name)
    try:
        joblib.dump(pipeline, temporary_model, compress=3)
        binary_hash = _sha256(temporary_model)
        binary_name = f"model-{binary_hash}.joblib"
        manifest = ModelManifest(
            schema_version=MANIFEST_SCHEMA_VERSION,
            model_version=f"lightgbm-{binary_hash[:16]}",
            contract_version=contract_version,
            created_at=datetime.now(UTC),
            model_file=binary_name,
            binary_sha256=binary_hash,
            data_version=data_version,
            fixture_hash=fixture_hash,
            **metadata,
        )
        os.replace(temporary_model, folder / binary_name)
    finally:
        temporary_model.unlink(missing_ok=True)

    # Write last: if interrupted, the old manifest still points to its old hash.
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=folder, prefix=".manifest-", suffix=".json", delete=False
    ) as temp:
        temporary_manifest = Path(temp.name)
        try:
            temp.write(
                json.dumps(
                    manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, allow_nan=False
                )
            )
            temp.write("\n")
            temp.flush()
            os.fsync(temp.fileno())
        except BaseException:
            temporary_manifest.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary_manifest, folder / MANIFEST_FILENAME)
    finally:
        temporary_manifest.unlink(missing_ok=True)
    return manifest


def read_manifest(directory: Path | str) -> ModelManifest:
    """Read JSON metadata safely, without deserializing the binary model."""
    path = Path(directory) / MANIFEST_FILENAME
    try:
        return ModelManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"invalid model manifest: {exc}") from exc


def load_pipeline(
    directory: Path | str, expected_contract_version: str = DEFAULT_CONTRACT_VERSION
) -> TrainedPipeline:
    """Load a verified artifact produced by a trusted V-EV Flow checkout."""
    manifest = read_manifest(directory)
    if manifest.contract_version != expected_contract_version:
        raise ValueError(
            f"contract version mismatch: expected {expected_contract_version!r}, "
            f"found {manifest.contract_version!r}"
        )
    _verify_feature_order(manifest.feature_columns)
    binary_path = Path(directory) / manifest.model_file
    if not binary_path.is_file():
        raise FileNotFoundError(f"missing model artifact: {binary_path}")
    if _sha256(binary_path) != manifest.binary_sha256:
        raise ValueError("model artifact SHA-256 checksum mismatch")

    loaded = joblib.load(binary_path)
    if not isinstance(loaded, TrainedPipeline):
        raise ValueError("model artifact does not contain a TrainedPipeline")
    for field, actual in _pipeline_metadata(loaded).items():
        if getattr(manifest, field) != actual:
            raise ValueError(f"model artifact metadata mismatch: {field}")
    return loaded
