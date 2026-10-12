import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from app.backend.modules.simulation.cli import main


def run_module(module: str, *args: str) -> None:
    subprocess.run([sys.executable, "-m", module, *args], check=True, capture_output=True)


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("generated")
    run_module(
        "app.backend.modules.station_data.cli",
        "generate", "--history-days", "2", "--vehicles", "30", "--output", str(out),
    )  # fmt: skip
    return out


def test_history_command_writes_parquet_and_updates_manifest(
    generated: Path,
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    assert main(["history", "--input", str(generated), "--output", str(tmp_path)]) == 0
    assert str(tmp_path / "manifest.json") in capsys.readouterr().out
    frame = pd.read_parquet(tmp_path / "station_status.parquet")
    assert set(frame["scenario"]) == {"normal", "holiday_30_4", "tet"}
    assert not frame.duplicated(subset=["scenario", "station_id", "ts"]).any()
    summary = json.loads((tmp_path / "manifest.json").read_text())
    assert summary["status_history"]["rows"] == len(frame)
    digest = hashlib.sha256((tmp_path / "station_status.parquet").read_bytes()).hexdigest()
    assert summary["status_history"]["sha256"] == digest
    assert summary["data_type"] == "simulated"


def test_history_is_reproducible(generated: Path, tmp_path: Path) -> None:
    for name in ("a", "b"):
        assert main(["history", "--input", str(generated), "--output", str(tmp_path / name)]) == 0
    first = pd.read_parquet(tmp_path / "a" / "station_status.parquet")
    second = pd.read_parquet(tmp_path / "b" / "station_status.parquet")
    pd.testing.assert_frame_equal(first, second)


def test_history_without_input_manifest_fails(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    assert main(["history", "--input", str(tmp_path)]) == 2
    assert "station_data.cli generate" in capsys.readouterr().err


def test_history_rejects_tampered_bundle(generated: Path, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    copy = tmp_path / "copy"
    subprocess.run(["cp", "-R", str(generated), str(copy)], check=True)
    bundle = copy / "normal" / "fixture_bundle.json"
    payload = json.loads(bundle.read_text())
    payload["seed"] = 999
    bundle.write_text(json.dumps(payload))
    assert main(["history", "--input", str(copy)]) == 2
    assert "hash mismatch" in capsys.readouterr().err


def test_compare_command_reports_baselines_and_is_reproducible(
    generated: Path,
    tmp_path: Path,
    capsys,  # noqa: ANN001
) -> None:
    for name in ("a", "b"):
        args = ["compare", "--input", str(generated), "--scenario", "all", "--vehicles", "20"]
        assert main([*args, "--output", str(tmp_path / name)]) == 0
    out = capsys.readouterr().out
    assert "nearest" in out and "currently_available" in out and "fixture_hash" in out
    first = json.loads((tmp_path / "a" / "compare_results.json").read_text())
    assert first == json.loads((tmp_path / "b" / "compare_results.json").read_text())
    assert len(first) == 6  # 3 scenarios x 2 baselines; ai_allocation needs --ai-strategy
    assert {item["strategy"] for item in first} == {"nearest", "currently_available"}
    assert all(item["metrics"]["vehicle_count"] == 20 for item in first)
    manifest = json.loads((generated / "manifest.json").read_text())
    for item in first:
        assert item["fixture_hash"] == manifest["scenarios"][item["scenario"]]["fixture_hash"]


def test_compare_accepts_injected_ai_strategy(generated: Path, tmp_path: Path) -> None:
    args = ["compare", "--input", str(generated), "--vehicles", "10", "--output", str(tmp_path)]
    ai = "app.backend.modules.simulation.baselines:NearestStrategy"
    assert main([*args, "--ai-strategy", ai]) == 0
    results = json.loads((tmp_path / "compare_results.json").read_text())
    assert {item["strategy"] for item in results} == {
        "nearest", "currently_available", "ai_allocation"
    }  # fmt: skip


def test_compare_rejects_bad_input(generated: Path, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    assert main(["compare", "--input", str(tmp_path)]) == 2
    assert main(["compare", "--input", str(generated), "--ai-strategy", "nocolon"]) == 2
    assert main(["compare", "--input", str(generated), "--vehicles", "31"]) == 2
    assert "error" in capsys.readouterr().err
