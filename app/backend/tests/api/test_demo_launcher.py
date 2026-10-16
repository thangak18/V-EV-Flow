"""The release launcher must not depend on an OS temporary data directory."""

import sys
from pathlib import Path

from fastapi import FastAPI

from app.backend.api import demo
from app.backend.core.settings import Settings


def test_launcher_keeps_runtime_snapshots_in_workspace_and_cleans_its_session(
    tmp_path, monkeypatch
):
    release = tmp_path / "release"
    for name in [
        "model/manifest.json",
        "data/stations.json",
        "data/station_status.parquet",
        "data/manifest.json",
        "producer_scenarios.yaml",
    ]:
        path = release / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"mock fixture")
    parent = tmp_path / "workspace" / "runtime"
    captured = []

    def create(settings: Settings):
        captured.append(settings.data_dir)
        assert settings.data_dir.is_relative_to(parent)
        assert (
            settings.data_dir / "generated/station_status.parquet"
        ).read_bytes() == b"mock fixture"
        return FastAPI()

    monkeypatch.setattr(
        sys, "argv", ["demo", "--release-dir", str(release), "--runtime-dir", str(parent)]
    )
    monkeypatch.setattr(demo, "create_app", create)
    monkeypatch.setattr(demo.uvicorn, "run", lambda *args, **kwargs: None)
    demo.main()
    assert parent.is_dir()
    assert not captured[0].exists()
    assert (release / "data/station_status.parquet").read_bytes() == b"mock fixture"
