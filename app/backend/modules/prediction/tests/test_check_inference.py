"""Acceptance runner exercises real tiny pipelines without committed binaries."""

from datetime import datetime
from pathlib import Path

import pytest

from app.backend.modules.prediction.check_inference import main, run_cases
from app.backend.modules.prediction.demo import build_demo


@pytest.fixture(scope="module")
def acceptance_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    folder = tmp_path_factory.mktemp("inference-acceptance")
    build_demo(folder, seed=42, days=3)
    return folder


def test_matrix_covers_scenarios_and_distinct_failure_layers(acceptance_bundle: Path) -> None:
    report = run_cases(
        acceptance_bundle / "model",
        acceptance_bundle / "stations.json",
        acceptance_bundle / "station_status.parquet",
        datetime.fromisoformat("2026-10-13T16:00:00+07:00"),
    )
    assert report["passed"] and report["inputs_unchanged"]
    assert report["case_count"] == report["passed_count"] == 24
    cases = {case["case_id"]: case for case in report["cases"]}
    for scenario in ("normal", "holiday_30_4", "tet"):
        for horizon in (15, 30, 60):
            case = cases[f"valid_{scenario}_{horizon}"]
            assert case["response"]["data_type"] == "simulated"
            assert case["request"]["scenario"] == scenario
            assert case["response"]["model_version"] == report["model_version"]
    for lag in (15, 30, 60):
        assert "response" in cases[f"partial_window_missing_{lag}"]
        assert cases[f"file_repository_missing_{lag}"]["error"]["type"] == (
            "DataSourceUnavailableError"
        )
    assert "response" in cases["partial_window_missing_15_30_60"]
    assert cases["partial_window_missing_0"]["error"]["type"] == "ValueError"
    assert cases["file_repository_missing_0"]["error"]["type"] == "DataSourceUnavailableError"
    for failure in ("missing_manifest", "missing_binary", "bad_checksum", "invalid_manifest"):
        case = cases[f"artifact_{failure}"]
        assert "response" not in case
        assert case["passed"]
        assert str(acceptance_bundle) not in case["error"]["message"]


def test_missing_artifact_is_setup_failure_not_false_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "report.json"
    rc = main(
        [
            "--model-dir",
            str(tmp_path / "absent"),
            "--stations",
            str(tmp_path / "stations.json"),
            "--status",
            str(tmp_path / "status.parquet"),
            "--observed-at",
            "2026-10-13T16:00:00+07:00",
            "--output",
            str(output),
        ]
    )
    assert rc == 2 and not output.exists()
    assert "setup failed" in capsys.readouterr().err


def test_report_cannot_overwrite_inputs(acceptance_bundle: Path) -> None:
    stations = acceptance_bundle / "stations.json"
    original = stations.read_bytes()
    rc = main(
        [
            "--model-dir",
            str(acceptance_bundle / "model"),
            "--stations",
            str(stations),
            "--status",
            str(acceptance_bundle / "station_status.parquet"),
            "--observed-at",
            "2026-10-13T16:00:00+07:00",
            "--output",
            str(stations),
        ]
    )
    assert rc == 2 and stations.read_bytes() == original
