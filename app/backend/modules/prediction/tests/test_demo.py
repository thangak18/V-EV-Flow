"""Demo model delivery and deterministic synthetic provenance checks."""

import json
from pathlib import Path

import pandas as pd

from app.backend.modules.prediction.artifacts import load_pipeline, read_manifest
from app.backend.modules.prediction.demo import SOURCE, build_demo, generate_fixture


def test_reproducible_fixture_and_end_to_end_demo(tmp_path: Path) -> None:
    stations, status = generate_fixture(seed=42, days=3)
    repeat_stations, repeat = generate_fixture(seed=42, days=3)
    assert stations == repeat_stations
    pd.testing.assert_frame_equal(status, repeat)
    assert set(status["scenario"]) == {"normal", "holiday_30_4", "tet"}
    model_dir = build_demo(tmp_path, seed=42, days=3)
    manifest = read_manifest(model_dir)
    assert manifest.source == SOURCE
    assert manifest.data_type == "simulated"
    assert manifest.split_metadata["max_horizon_minutes"] == 60
    assert all(v["log_loss"] >= 0 for v in manifest.test_metrics.values())
    assert load_pipeline(model_dir).feature_columns == tuple(manifest.feature_columns)
    result = json.loads((tmp_path / "prediction.json").read_text())
    assert 0 <= result["p_available"] <= 1
    assert result["model_version"] == manifest.model_version
    assert result["data_type"] == "simulated"
    assert "Log Loss" in (tmp_path / "report.md").read_text()
