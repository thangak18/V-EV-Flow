"""Versioned model artifacts: reproducibility, round trip, and corruption checks."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.backend.contracts.stations import Station
from app.backend.modules.prediction.artifacts import (
    ModelManifest,
    load_pipeline,
    read_manifest,
    save_pipeline,
)
from app.backend.modules.prediction.dataset import validate_status_frame
from app.backend.modules.prediction.features import FEATURE_COLUMNS
from app.backend.modules.prediction.labels import build_labels
from app.backend.modules.prediction.split import temporal_split
from app.backend.modules.prediction.training import TrainingConfig, train_candidate


@pytest.fixture(scope="module")
def trained_and_features():  # noqa: ANN201
    stations = tuple(
        Station.model_validate(
            {
                "station_id": f"S00{index}",
                "name": f"Test station {index}",
                "lat": 10.0 + index / 10,
                "lng": 107.0,
                "n_ports": 3,
                "power_kw": 120.0,
                "connector_types": ["CCS2"],
                "network": "mock",
                "station_type": "highway",
                "source": "synthetic-test",
                "assumptions": ["one connector type"],
            }
        )
        for index in (1, 2)
    )
    random = np.random.default_rng(24)
    records = []
    start = pd.Timestamp("2026-10-12T00:00:00+07:00")
    for scenario in ("normal", "tet"):
        for station in stations:
            for tick in range(320):
                ts = start + pd.Timedelta(minutes=5 * tick)
                free = int(random.binomial(station.n_ports, 0.40 if scenario == "normal" else 0.20))
                records.append(
                    {
                        "station_id": station.station_id,
                        "scenario": scenario,
                        "ts": ts,
                        "ports_free": free,
                        "ports_busy": station.n_ports - free,
                        "ports_broken": 0,
                    }
                )
    status = validate_status_frame(pd.DataFrame(records), stations)
    split = temporal_split(
        build_labels(status, [15, 30]),
        train_end="2026-10-12T08:00:00+07:00",
        calibration_end="2026-10-12T17:00:00+07:00",
        max_horizon_minutes=30,
    )
    trained = train_candidate(
        split,
        TrainingConfig(n_estimators=14, min_child_samples=4, source="synthetic-artifacts-test"),
        status_frame=status,
        stations=stations,
        seed=24,
    )
    features = trained.feature_builder.build(status, split.test).X
    return trained, features


def test_round_trip_and_complete_manifest(trained_and_features, tmp_path: Path) -> None:  # noqa: ANN001
    trained, features = trained_and_features
    fixture_hash = hashlib.sha256(b"fixture-v1").hexdigest()
    saved = save_pipeline(
        trained,
        tmp_path,
        data_version="synthetic-v1",
        fixture_hash=fixture_hash,
    )
    assert isinstance(saved, ModelManifest)
    assert saved.schema_version == "1"
    assert saved.contract_version == "0.1.0"
    assert saved.model_version.startswith("lightgbm-")
    assert saved.model_class == "LGBMClassifier"
    assert saved.calibration_method == trained.calibration_method
    assert saved.data_version == "synthetic-v1"
    assert saved.fixture_hash == fixture_hash
    assert saved.feature_columns == list(FEATURE_COLUMNS)
    assert saved.lag_fill_values == trained.feature_builder.lag_fill_values
    assert saved.training_config["random_state"] == 42
    assert saved.split_metadata["counts"] == trained.sample_counts
    assert saved.test_metrics["lightgbm_raw"]["sample_count"] == len(features)

    manifest_path = tmp_path / "manifest.json"
    assert (
        json.loads(manifest_path.read_text(encoding="utf-8"))["binary_sha256"]
        == saved.binary_sha256
    )
    assert read_manifest(tmp_path) == saved
    binary = tmp_path / saved.model_file
    assert binary.is_file()
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == saved.binary_sha256

    loaded = load_pipeline(tmp_path, expected_contract_version="0.1.0")
    np.testing.assert_allclose(trained.predict_proba(features), loaded.predict_proba(features))
    assert loaded.test_metrics == trained.test_metrics
    assert loaded.feature_columns == trained.feature_columns
    assert loaded.feature_builder.lag_fill_values == trained.feature_builder.lag_fill_values
    assert loaded.hourly_baseline.hourly_rates == trained.hourly_baseline.hourly_rates


def test_rejects_contract_and_manifest_schema_before_unpickling(
    trained_and_features, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ANN001
    save_pipeline(trained_and_features[0], tmp_path)

    def no_unpickle(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not unpickle on metadata mismatch")

    monkeypatch.setattr("app.backend.modules.prediction.artifacts.joblib.load", no_unpickle)
    with pytest.raises(ValueError, match="contract version"):
        load_pipeline(tmp_path, expected_contract_version="999.0")

    path = tmp_path / "manifest.json"
    altered = json.loads(path.read_text(encoding="utf-8"))
    altered["schema_version"] = "9000"
    path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest|schema"):
        load_pipeline(tmp_path, expected_contract_version="0.1.0")


def test_rejects_feature_order_before_unpickling(
    trained_and_features, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:  # noqa: ANN001
    save_pipeline(trained_and_features[0], tmp_path)
    path = tmp_path / "manifest.json"
    altered = json.loads(path.read_text(encoding="utf-8"))
    altered["feature_columns"] = list(reversed(altered["feature_columns"]))
    path.write_text(json.dumps(altered), encoding="utf-8")

    def no_unpickle(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not unpickle on feature mismatch")

    monkeypatch.setattr("app.backend.modules.prediction.artifacts.joblib.load", no_unpickle)
    with pytest.raises(ValueError, match="feature.*order"):
        load_pipeline(tmp_path, expected_contract_version="0.1.0")


def test_rejects_missing_and_tampered_binary(trained_and_features, tmp_path: Path) -> None:  # noqa: ANN001
    manifest = save_pipeline(trained_and_features[0], tmp_path)
    binary = tmp_path / manifest.model_file
    binary.write_bytes(binary.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="SHA-256|checksum"):
        load_pipeline(tmp_path, expected_contract_version="0.1.0")
    binary.unlink()
    with pytest.raises(FileNotFoundError, match="model|artifact"):
        load_pipeline(tmp_path, expected_contract_version="0.1.0")


def test_rejects_invalid_input_and_manifest_path_traversal(
    trained_and_features, tmp_path: Path
) -> None:  # noqa: ANN001
    with pytest.raises(ValueError, match="fixture_hash"):
        save_pipeline(trained_and_features[0], tmp_path, fixture_hash="not-a-hash")
    with pytest.raises(ValueError, match="data_version"):
        save_pipeline(trained_and_features[0], tmp_path, data_version="")

    save_pipeline(trained_and_features[0], tmp_path)
    manifest = tmp_path / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["model_file"] = "../../outside.joblib"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest|model_file"):
        load_pipeline(tmp_path, expected_contract_version="0.1.0")


def test_rejects_metadata_tampering_and_missing_schema(
    trained_and_features, tmp_path: Path
) -> None:  # noqa: ANN001
    save_pipeline(trained_and_features[0], tmp_path)
    manifest = tmp_path / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["source"] = "altered-source"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata mismatch: source"):
        load_pipeline(tmp_path)

    del data["schema_version"]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"):
        read_manifest(tmp_path)


def test_replacement_publishes_new_manifest_last_and_keeps_previous_binary(
    trained_and_features, tmp_path: Path
) -> None:  # noqa: ANN001
    trained, features = trained_and_features
    old = save_pipeline(trained, tmp_path)
    replacement = replace(trained, source="second-fixture")
    current = save_pipeline(replacement, tmp_path)
    assert current.model_version != old.model_version
    assert current.model_file != old.model_file
    assert (tmp_path / old.model_file).is_file()
    assert (tmp_path / current.model_file).is_file()
    assert read_manifest(tmp_path) == current
    loaded = load_pipeline(tmp_path)
    assert loaded.source == "second-fixture"
    np.testing.assert_allclose(loaded.predict_proba(features), replacement.predict_proba(features))


def test_legacy_metric_reports_remain_loadable(trained_and_features, tmp_path: Path) -> None:  # noqa: ANN001
    trained, features = trained_and_features
    legacy = replace(
        trained,
        test_metrics={
            name: replace(metric, log_loss=None) for name, metric in trained.test_metrics.items()
        },
    )
    manifest = save_pipeline(legacy, tmp_path)
    assert "log_loss" not in manifest.test_metrics["lightgbm_calibrated"]
    loaded = load_pipeline(tmp_path)
    assert loaded.test_metrics["lightgbm_calibrated"].log_loss is None
    np.testing.assert_allclose(loaded.predict_proba(features), trained.predict_proba(features))
