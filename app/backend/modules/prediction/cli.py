"""Train, evaluate and predict from explicitly sourced CSV/Parquet histories.

Run with ``python -m app.backend.modules.prediction.cli``. Artifacts are local
trusted joblib files; generated datasets and model binaries stay out of Git.
"""

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

import pandas as pd

from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.prediction import PredictRequest
from app.backend.contracts.recommendation import StatusWindow
from app.backend.contracts.stations import Station, StationStatus
from app.backend.modules.prediction.artifacts import load_pipeline, read_manifest, save_pipeline
from app.backend.modules.prediction.dataset import load_status_frame, validate_status_frame
from app.backend.modules.prediction.labels import build_labels
from app.backend.modules.prediction.public import load_predictor
from app.backend.modules.prediction.split import temporal_split
from app.backend.modules.prediction.training import (
    DataType as TrainingDataType,
)
from app.backend.modules.prediction.training import (
    TrainingConfig,
    evaluate_holdout,
    train_candidate,
)


class _FileStations:
    def __init__(self, path: Path) -> None:
        records = json.loads(path.read_text(encoding="utf-8"))
        self.stations = tuple(Station.model_validate(row) for row in records)
        self.by_id = {station.station_id: station for station in self.stations}
        if len(self.by_id) != len(self.stations):
            raise ValueError("duplicate station_id in station metadata")

    def list_stations(self) -> tuple[Station, ...]:
        return self.stations

    def get_station(self, station_id: str) -> Station:
        return self.by_id[station_id]


class _FileStatuses:
    def __init__(self, frame: pd.DataFrame, stations: _FileStations, scenario: Scenario) -> None:
        self.frame = frame
        self.stations = stations
        self.scenario = scenario

    def window(
        self, station_id: str, observed_at: datetime, lags: tuple[int, ...] = (15, 30, 60)
    ) -> StatusWindow:
        times = [observed_at - timedelta(minutes=lag) for lag in lags]
        rows = self.frame.loc[
            (self.frame["station_id"] == station_id)
            & (self.frame["scenario"] == self.scenario.value)
            & self.frame["ts"].isin(times)
        ]
        capacity = self.stations.get_station(station_id).n_ports
        statuses = tuple(
            StationStatus.model_validate({**row, "n_ports": capacity})
            for row in rows.to_dict(orient="records")
        )
        return StatusWindow(
            station_id=station_id, observed_at=observed_at, lags=lags, statuses=statuses
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("train", "evaluate", "predict"):
        sub = commands.add_parser(command)
        sub.add_argument("--stations", type=Path, required=True)
        sub.add_argument("--status", type=Path, required=True)
        if command == "train":
            sub.add_argument("--artifact-dir", type=Path, required=True)
            sub.add_argument("--train-end", required=True)
            sub.add_argument("--calibration-end", required=True)
            sub.add_argument("--data-version", default="unspecified")
        else:
            sub.add_argument("--model-dir", type=Path, required=True)
        if command in ("train", "evaluate"):
            sub.add_argument("--horizons", default="15,30,60")
            sub.add_argument("--source", required=True)
            sub.add_argument(
                "--data-type", choices=[item.value for item in DataType], default="simulated"
            )
            sub.add_argument("--seed", type=int, default=42)
        else:
            sub.add_argument("--station-id", required=True)
            sub.add_argument("--observed-at", required=True)
            sub.add_argument("--eta", required=True)
            sub.add_argument("--connector-type", required=True)
            sub.add_argument("--scenario", choices=[item.value for item in Scenario], required=True)
            sub.add_argument(
                "--status-data-type", choices=[item.value for item in DataType], required=True
            )
    return parser


def _run(args: argparse.Namespace) -> dict[str, object]:
    stations = _FileStations(args.stations)
    frame = validate_status_frame(load_status_frame(args.status), stations.stations)
    if args.command == "predict":
        scenario = Scenario(args.scenario)
        predictor = load_predictor(
            args.model_dir,
            _FileStatuses(frame, stations, scenario),
            stations,
            status_data_type=DataType(args.status_data_type),
        )
        request = PredictRequest(
            station_id=args.station_id,
            observed_at=datetime.fromisoformat(args.observed_at),
            eta=datetime.fromisoformat(args.eta),
            connector_type=args.connector_type,
            scenario=scenario,
        )
        return predictor.predict(request).model_dump(mode="json")

    try:
        horizons = [int(value.strip()) for value in args.horizons.split(",")]
    except ValueError as exc:
        raise ValueError("horizons must be comma-separated integer minutes") from exc
    labels = build_labels(frame, horizons)
    data_type = cast(TrainingDataType, args.data_type)
    if args.command == "train":
        split = temporal_split(
            labels,
            train_end=args.train_end,
            calibration_end=args.calibration_end,
            max_horizon_minutes=max(horizons),
        )
        pipeline = train_candidate(
            split,
            TrainingConfig(random_state=args.seed, data_type=data_type, source=args.source),
            status_frame=frame,
            stations=stations.stations,
            seed=args.seed,
        )
        # Digest actual station metadata and history bytes, with length framing.
        digest = hashlib.sha256()
        for path in (args.stations, args.status):
            payload = path.read_bytes()
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
        manifest = save_pipeline(
            pipeline,
            args.artifact_dir,
            data_version=args.data_version,
            fixture_hash=digest.hexdigest(),
        )
        return {
            "model_version": manifest.model_version,
            "data_type": manifest.data_type,
            "source": manifest.source,
            "split_counts": manifest.sample_counts,
            "split_metadata": manifest.split_metadata,
            "test_metrics": manifest.test_metrics,
            "artifact_dir": str(args.artifact_dir),
        }

    manifest = read_manifest(args.model_dir)
    pipeline = load_pipeline(args.model_dir)
    if max(horizons) > pipeline.split_metadata.max_horizon_minutes:
        raise ValueError("evaluation horizon exceeds trained maximum horizon")
    # A caller cannot accidentally evaluate on training/calibration/test periods.
    if frame["ts"].min() <= pipeline.split_metadata.observed_ranges["test"][1]:
        raise ValueError("evaluation must use a separate timeline after the training test period")
    report = evaluate_holdout(
        pipeline, frame, labels, source=args.source, data_type=data_type, seed=args.seed
    )
    return {
        "model_version": manifest.model_version,
        "sample_count": report.sample_count,
        "data_type": report.data_type,
        "source": report.source,
        "seed": report.seed,
        "scenarios": list(report.scenarios),
        "observed_range": [value.isoformat() for value in report.observed_range],
        "metrics": {name: asdict(metric) for name, metric in report.metrics.items()},
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        summary = _run(args)
        print(json.dumps(summary, ensure_ascii=False, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
