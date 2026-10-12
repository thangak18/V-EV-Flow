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
        "generate", "--history-days", "2", "--vehicles", "0", "--output", str(out),
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
