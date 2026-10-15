"""Build a separately trained capacity counterfactual from the original event fixtures.

This is an offline experiment. It changes station metadata and regenerates
background histories, then uses the parent's time cutoffs and horizons. It does
not train on foreground vehicle outcomes or choose a model from what-if wins.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from app.backend.contracts.simulation import FixtureBundle, ScenarioConfig
from app.backend.contracts.stations import Station
from app.backend.modules.prediction.public import read_manifest
from app.backend.modules.simulation.public import generate_status_history


def build_variant(release: Path, output: Path, station_id: str, ports: int) -> dict:
    if isinstance(ports, bool) or not isinstance(ports, int) or not 1 <= ports <= 20:
        raise ValueError("added ports must be an integer between 1 and 20")
    if output.exists():
        raise ValueError("variant output must be a new immutable directory")
    parent = read_manifest(release / "model")
    stations = [
        Station.model_validate(row)
        for row in json.loads((release / "data/stations.json").read_text())
    ]
    if station_id not in {station.station_id for station in stations}:
        raise ValueError("unknown station")
    stations = [
        station.model_copy(update={"n_ports": station.n_ports + ports})
        if station.station_id == station_id
        else station
        for station in stations
    ]
    producer = json.loads((release / "data/manifest.json").read_text())
    frames = []
    for name, entry in producer["scenarios"].items():
        bundle = FixtureBundle.model_validate_json(
            (release / f"data/{name}/fixture_bundle.json").read_text()
        )
        frames.append(
            generate_status_history(
                bundle, stations, ScenarioConfig.model_validate(entry["config"])
            )
        )
    output.mkdir(parents=True)
    station_path, history_path = output / "stations.json", output / "station_status.parquet"
    station_path.write_text(json.dumps([station.model_dump(mode="json") for station in stations]))
    pd.concat(frames, ignore_index=True).to_parquet(history_path, index=False)
    maximum = int(parent.split_metadata["max_horizon_minutes"])
    horizons = sorted({15, 30, 60, maximum, *([90, 120] if maximum >= 120 else [])})
    arguments = [
        sys.executable,
        "-m",
        "app.backend.modules.prediction.cli",
        "train",
        "--stations",
        str(station_path),
        "--status",
        str(history_path),
        "--artifact-dir",
        str(output / "model"),
        "--train-end",
        str(parent.split_metadata["train_end"]),
        "--calibration-end",
        str(parent.split_metadata["calibration_end"]),
        "--horizons",
        ",".join(map(str, horizons)),
        "--source",
        "bao-capacity-counterfactual",
        "--data-type",
        "simulated",
        "--data-version",
        parent.data_version + f"-{station_id}-plus{ports}",
        "--seed",
        "42",
    ]
    trained = subprocess.run(arguments, capture_output=True, text=True, check=True)
    report = json.loads(trained.stdout)
    (output / "training_report.json").write_text(json.dumps(report, indent=2))
    declaration = {
        "station_id": station_id,
        "ports": ports,
        "data_type": "simulated",
        "base_model_sha256": parent.binary_sha256,
        "model_version": report["model_version"],
        "stations_sha256": hashlib.sha256(station_path.read_bytes()).hexdigest(),
        "history_sha256": hashlib.sha256(history_path.read_bytes()).hexdigest(),
        "assumptions": [
            "same background arrival/service/fault trace as original training fixtures",
            "added ports have no new independent fault trace",
            "training/calibration cutoffs copied from the parent model",
            "changing capacity and retraining changes both infrastructure and predictor",
        ],
    }
    (output / "variant.json").write_text(json.dumps(declaration, indent=2))
    return declaration


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--station-id", default="S001")
    parser.add_argument("--ports", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(build_variant(args.release_dir, args.output, args.station_id, args.ports)))


if __name__ == "__main__":
    main()
