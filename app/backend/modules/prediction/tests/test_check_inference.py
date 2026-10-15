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


def test_capability_checks_are_not_file_runtime_acceptance(acceptance_bundle: Path) -> None:
    report = run_cases(
        acceptance_bundle / "model",
        acceptance_bundle / "stations.json",
        acceptance_bundle / "station_status.parquet",
        datetime.fromisoformat("2026-10-13T16:00:00+07:00"),
    )
    assert report["runtime_check_count"] == 19
    assert report["capability_check_count"] == 5
    partial = [c for c in report["cases"] if c["category"] == "capability_only"]
    assert len(partial) == 5 and all(not c["runtime_accepted"] for c in partial)


@pytest.mark.parametrize("mutation", ["version", "probability", "unexpected_success"])
def test_runner_detects_incorrect_predictions(
    acceptance_bundle: Path, monkeypatch, mutation: str
) -> None:
    from app.backend.modules.prediction.predictor import ModelPredictor

    original = ModelPredictor.predict

    def predict(self, request):
        if (
            mutation == "unexpected_success"
            and (request.eta - request.observed_at).total_seconds() > 3600
        ):
            request = request.model_copy(update={"eta": request.observed_at.replace(minute=30)})
        result = original(self, request)
        if mutation == "version":
            return result.model_copy(update={"model_version": "wrong"})
        if mutation == "probability":
            return result.model_copy(update={"p_available": 1.5})
        return result

    monkeypatch.setattr(ModelPredictor, "predict", predict)
    report = run_cases(
        acceptance_bundle / "model",
        acceptance_bundle / "stations.json",
        acceptance_bundle / "station_status.parquet",
        datetime.fromisoformat("2026-10-13T16:00:00+07:00"),
    )
    assert not report["passed"] and report["passed_count"] < report["case_count"]


@pytest.mark.parametrize("passed,exit_code", [(True, 0), (False, 1)])
def test_main_writes_verdict(tmp_path: Path, monkeypatch, passed: bool, exit_code: int) -> None:
    import json

    from app.backend.modules.prediction import check_inference as module

    monkeypatch.setattr(
        module,
        "run_cases",
        lambda *a: {"passed": passed, "passed_count": int(passed), "case_count": 1},
    )
    output = tmp_path / "output.json"
    assert (
        module.main(
            [
                "--model-dir",
                str(tmp_path / "model"),
                "--stations",
                str(tmp_path / "stations"),
                "--status",
                str(tmp_path / "status"),
                "--observed-at",
                "2026-10-13T16:00:00+07:00",
                "--output",
                str(output),
            ]
        )
        == exit_code
    )
    assert json.loads(output.read_text())["passed"] is passed


@pytest.mark.parametrize("error", [KeyError("max_horizon_minutes"), TypeError("bad metadata")])
def test_main_metadata_error_is_setup_failure(
    tmp_path: Path, monkeypatch, error: Exception
) -> None:
    from app.backend.modules.prediction import check_inference as module

    def fail(*args):
        raise error

    monkeypatch.setattr(module, "run_cases", fail)
    output = tmp_path / "output.json"
    assert (
        module.main(
            [
                "--model-dir",
                str(tmp_path / "model"),
                "--stations",
                str(tmp_path / "stations"),
                "--status",
                str(tmp_path / "status"),
                "--observed-at",
                "2026-10-13T16:00:00+07:00",
                "--output",
                str(output),
            ]
        )
        == 2
    )
    assert not output.exists()


def test_reports_redact_resolved_and_input_paths(
    acceptance_bundle: Path, tmp_path: Path, monkeypatch
) -> None:
    from app.backend.modules.prediction.predictor import ModelPredictor

    alias = tmp_path / "model-alias"
    alias.symlink_to(acceptance_bundle / "model", target_is_directory=True)

    def fail(self, request):
        raise ValueError(f"{alias}/model.joblib and {alias.resolve()}/manifest.json")

    monkeypatch.setattr(ModelPredictor, "predict", fail)
    report = run_cases(
        alias,
        acceptance_bundle / "stations.json",
        acceptance_bundle / "station_status.parquet",
        datetime.fromisoformat("2026-10-13T16:00:00+07:00"),
    )
    message = report["cases"][0]["error"]["message"]
    assert "<local-path>" in message
    assert str(alias) not in message and str(alias.resolve()) not in message


def test_runner_fails_when_corrupt_artifact_is_accepted(
    acceptance_bundle: Path, monkeypatch
) -> None:
    from app.backend.modules.prediction import check_inference as module

    original = module.load_predictor

    def bypass_checksum(directory, *args, **kwargs):
        if Path(directory).name == "bad_checksum":
            directory = acceptance_bundle / "model"
        return original(directory, *args, **kwargs)

    monkeypatch.setattr(module, "load_predictor", bypass_checksum)
    report = module.run_cases(
        acceptance_bundle / "model",
        acceptance_bundle / "stations.json",
        acceptance_bundle / "station_status.parquet",
        datetime.fromisoformat("2026-10-13T16:00:00+07:00"),
    )
    case = next(c for c in report["cases"] if c["case_id"] == "artifact_bad_checksum")
    assert not case["passed"] and not report["passed"]
