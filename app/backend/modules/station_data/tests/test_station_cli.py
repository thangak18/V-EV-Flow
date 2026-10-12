import json
import subprocess
import sys
from pathlib import Path

from app.backend.contracts.simulation import DataManifest, FixtureBundle
from app.backend.modules.station_data.cli import main
from app.backend.modules.station_data.manifests import fixture_hash


def test_generate_writes_stations_bundles_and_manifests(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    assert (
        main(["generate", "--history-days", "1", "--vehicles", "5", "--output", str(tmp_path)]) == 0
    )
    assert str(tmp_path / "manifest.json") in capsys.readouterr().out
    summary = json.loads((tmp_path / "manifest.json").read_text())
    assert summary["data_type"] == "simulated"
    assert set(summary["scenarios"]) == {"normal", "holiday_30_4", "tet"}
    assert not (tmp_path / "station_status.parquet").exists()
    windows = {(e["config"]["start"], e["config"]["end"]) for e in summary["scenarios"].values()}
    assert len(windows) == 1  # shared calendar window for a global temporal split
    for name, entry in summary["scenarios"].items():
        manifest = DataManifest.model_validate(
            json.loads((tmp_path / name / "manifest.json").read_text())
        )
        bundle = FixtureBundle.model_validate_json(
            (tmp_path / name / "fixture_bundle.json").read_text()
        )
        assert manifest.fixture_hash == entry["fixture_hash"] == fixture_hash(bundle)
        assert len(bundle.vehicles) == 5


def test_generate_is_reproducible_across_processes(tmp_path: Path) -> None:
    hashes = []
    for run in ("a", "b"):
        out = tmp_path / run
        subprocess.run(
            [
                sys.executable,
                "-m",
                "app.backend.modules.station_data.cli",
                "generate",
                "--scenario",
                "normal",
                "--history-days",
                "1",
                "--output",
                str(out),
            ],
            check=True,
            capture_output=True,
        )
        hashes.append(
            json.loads((out / "manifest.json").read_text())["scenarios"]["normal"]["fixture_hash"]
        )
    assert hashes[0] == hashes[1]


def test_invalid_history_days_returns_nonzero(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    assert main(["generate", "--history-days", "0", "--output", str(tmp_path)]) == 2
    assert "error" in capsys.readouterr().err
