"""CLI train/evaluate/predict smoke using isolated synthetic status CSV files."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from app.backend.modules.prediction.artifacts import read_manifest
from app.backend.modules.prediction.cli import main
from app.backend.modules.prediction.tests.test_predictor import training_bundle  # noqa: F401, F811


@pytest.fixture
def cli_files(training_bundle, tmp_path: Path):  # noqa: ANN001, ANN201, F811
    stations, status, *_ = training_bundle
    stations_file = tmp_path / "stations.json"
    stations_file.write_text(
        json.dumps([station.model_dump() for station in stations]), encoding="utf-8"
    )
    status_file = tmp_path / "status.csv"
    status.to_csv(status_file, index=False)
    return stations_file, status_file, tmp_path / "artifact", status


def test_cli_train_evaluate_predict_roundtrip(
    cli_files, capsys: pytest.CaptureFixture[str]
) -> None:  # noqa: ANN001
    stations_file, status_file, artifact_dir, status = cli_files
    rc = main(
        [
            "train",
            "--stations",
            str(stations_file),
            "--status",
            str(status_file),
            "--artifact-dir",
            str(artifact_dir),
            "--train-end",
            "2026-10-12T09:00:00+07:00",
            "--calibration-end",
            "2026-10-12T19:00:00+07:00",
            "--horizons",
            "15,30",
            "--source",
            "synthetic-cli-test",
            "--data-type",
            "simulated",
            "--seed",
            "33",
            "--data-version",
            "cli-test-1",
        ],
    )
    assert rc == 0
    trained = json.loads(capsys.readouterr().out)
    assert trained["data_type"] == "simulated"
    assert trained["model_version"].startswith("lightgbm-")
    assert trained["split_counts"]["train"] > 0
    assert trained["test_metrics"]["lightgbm_calibrated"]["brier_score"] >= 0
    assert len(trained["test_metrics"]["lightgbm_calibrated"]["calibration"]) > 0
    assert read_manifest(artifact_dir).data_version == "cli-test-1"
    assert read_manifest(artifact_dir).fixture_hash is not None

    holdout = status.copy()
    holdout["ts"] = holdout["ts"] + pd.Timedelta(days=10)
    holdout_file = status_file.parent / "holdout.csv"
    holdout.to_csv(holdout_file, index=False)
    rc = main(
        [
            "evaluate",
            "--stations",
            str(stations_file),
            "--status",
            str(holdout_file),
            "--model-dir",
            str(artifact_dir),
            "--horizons",
            "15,30",
            "--source",
            "separate-simulated-fixture",
            "--data-type",
            "simulated",
            "--seed",
            "91",
        ]
    )
    assert rc == 0
    evaluation = json.loads(capsys.readouterr().out)
    assert evaluation["sample_count"] > 0
    assert evaluation["model_version"] == trained["model_version"]
    assert evaluation["source"] == "separate-simulated-fixture"
    assert set(evaluation["metrics"]) == {
        "lightgbm_raw",
        "lightgbm_calibrated",
        "persistence",
        "hourly_rate",
    }

    rc = main(
        [
            "predict",
            "--stations",
            str(stations_file),
            "--status",
            str(status_file),
            "--model-dir",
            str(artifact_dir),
            "--station-id",
            "S001",
            "--observed-at",
            "2026-10-13T00:00:00+07:00",
            "--eta",
            "2026-10-13T00:30:00+07:00",
            "--connector-type",
            "CCS2",
            "--scenario",
            "normal",
            "--status-data-type",
            "simulated",
        ]
    )
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert 0 <= result["p_available"] <= 1
    assert result["model_version"] == trained["model_version"]
    assert result["data_type"] == "simulated"


def test_cli_rejects_invalid_inputs(cli_files, capsys: pytest.CaptureFixture[str]) -> None:  # noqa: ANN001
    stations_file, status_file, artifact_dir, _status = cli_files
    rc = main(
        [
            "evaluate",
            "--stations",
            str(stations_file),
            "--status",
            str(status_file),
            "--model-dir",
            str(artifact_dir),
            "--source",
            "synthetic-evaluate",
        ]
    )
    assert rc == 2
    error = json.loads(capsys.readouterr().err)
    assert "error" in error


def test_cli_rejects_invalid_horizons(cli_files, capsys: pytest.CaptureFixture[str]) -> None:  # noqa: ANN001
    stations_file, status_file, artifact_dir, _status = cli_files
    rc = main(
        [
            "train",
            "--stations",
            str(stations_file),
            "--status",
            str(status_file),
            "--artifact-dir",
            str(artifact_dir),
            "--train-end",
            "2026-10-12T09:00:00+07:00",
            "--calibration-end",
            "2026-10-12T19:00:00+07:00",
            "--horizons",
            "13",
            "--source",
            "bad-horizons",
        ]
    )
    assert rc == 2
    assert "horizon" in capsys.readouterr().err


def test_module_entry_point() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.backend.modules.prediction.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "train" in result.stdout and "predict" in result.stdout


def test_evaluate_rejects_training_period(
    cli_files,
    training_bundle,  # noqa: F811
    capsys: pytest.CaptureFixture[str],  # noqa: F811
) -> None:  # noqa: ANN001
    stations_file, status_file, _artifact_dir, _status = cli_files
    rc = main(
        [
            "evaluate",
            "--stations",
            str(stations_file),
            "--status",
            str(status_file),
            "--model-dir",
            str(training_bundle[3]),
            "--horizons",
            "15,30",
            "--source",
            "overlapping-fixture",
        ]
    )
    assert rc == 2
    assert "separate timeline" in capsys.readouterr().err
