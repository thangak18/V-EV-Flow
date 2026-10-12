"""Simulation commands: ``python -m app.backend.modules.simulation.cli history``.

``history`` reads the output of ``app.backend.modules.station_data.cli
generate`` (stations, ``manifest.json``, per-scenario fixture bundles) as files
validated by shared contracts, replays each bundle through the engine, and
writes ``station_status.parquet``.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from app.backend.contracts.simulation import FixtureBundle, ScenarioConfig
from app.backend.contracts.stations import Station
from app.backend.modules.simulation.history import generate_status_history, write_status_history

STATUS_FILE = "station_status.parquet"
MANIFEST_FILE = "manifest.json"
BUNDLE_FILE = "fixture_bundle.json"


def build_history(input_dir: Path, output_dir: Path) -> dict[str, object]:
    manifest_path = input_dir / MANIFEST_FILE
    if not manifest_path.exists():
        raise ValueError(f"{manifest_path} not found; run station_data.cli generate first")
    summary = json.loads(manifest_path.read_text(encoding="utf-8"))
    stations = tuple(
        Station.model_validate(row)
        for row in json.loads((input_dir / "stations.json").read_text(encoding="utf-8"))
    )
    frames: list[pd.DataFrame] = []
    for name, entry in summary["scenarios"].items():
        config = ScenarioConfig.model_validate(entry["config"])
        bundle_path = input_dir / name / BUNDLE_FILE
        bundle = FixtureBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(bundle.model_dump_json().encode("utf-8")).hexdigest()
        if digest != entry["fixture_hash"]:
            raise ValueError(f"fixture hash mismatch for scenario {name}")
        frames.append(generate_status_history(bundle, stations, config))
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = write_status_history(
        pd.concat(frames, ignore_index=True), output_dir / STATUS_FILE
    )
    summary["status_history"] = {
        "file": STATUS_FILE,
        "rows": int(sum(len(frame) for frame in frames)),
        "sha256": hashlib.sha256(status_path.read_bytes()).hexdigest(),
    }
    (output_dir / MANIFEST_FILE).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simulation.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    history = commands.add_parser("history", help="write station_status.parquet from fixtures")
    history.add_argument("--input", type=Path, required=True, help="station_data.cli output dir")
    history.add_argument("--output", type=Path, default=None, help="default: same as --input")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = build_history(args.input, args.output or args.input)
    except (ValueError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print((args.output or args.input) / MANIFEST_FILE)
    print(json.dumps(summary["status_history"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
