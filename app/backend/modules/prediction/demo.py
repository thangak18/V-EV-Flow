"""Reproducible synthetic integration fixture; not the team's charging simulator.

Per-port busy/repair timers persist across five-minute ticks. There are no queues,
routes or driver strategies. This fixture supplies a trusted demo model while
waiting for Bảo's canonical simulator output; it cannot measure road accuracy.
"""

import argparse
import hashlib
import json
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd

from app.backend.contracts.stations import Station
from app.backend.modules.prediction.artifacts import save_pipeline
from app.backend.modules.prediction.cli import main as cli_main
from app.backend.modules.prediction.dataset import validate_status_frame
from app.backend.modules.prediction.labels import build_labels
from app.backend.modules.prediction.split import temporal_split
from app.backend.modules.prediction.training import TrainingConfig, train_candidate

SOURCE = "synthetic-correlated-integration-demo-v1"
START = pd.Timestamp("2026-10-12T00:00:00+07:00")


def generate_fixture(seed: int = 42, days: int = 7) -> tuple[tuple[Station, ...], pd.DataFrame]:
    if days < 3:
        raise ValueError("at least three days required for train/calibration/test")
    rng = np.random.default_rng(seed)
    stations = tuple(
        Station(
            station_id=f"S00{i}",
            name=f"Synthetic demo station {i}",
            lat=10.0 + i / 10,
            lng=107.0,
            n_ports=capacity,
            power_kw=120.0,
            connector_types=["CCS2"],
            network="synthetic-demo",
            station_type="highway",
            source=SOURCE,
            assumptions=["Synthetic location/capacity; uniform CCS2 ports"],
        )
        for i, capacity in ((1, 4), (2, 6), (3, 8))
    )
    records = []
    for scenario, multiplier in (("normal", 1.0), ("holiday_30_4", 1.5), ("tet", 2.0)):
        for station in stations:
            # A port cannot become free before its current session/repair expires.
            busy_until = np.zeros(station.n_ports, dtype=int)
            repair_until = np.zeros(station.n_ports, dtype=int)
            for tick in range(days * 288):
                ts = START + pd.Timedelta(minutes=tick * 5)
                faults = (rng.random(station.n_ports) < 0.001) & (repair_until <= tick)
                repair_until[faults] = tick + 12
                available = (busy_until <= tick) & (repair_until <= tick)
                pressure = (0.28 if 15 <= ts.hour <= 21 else 0.12) * multiplier
                arrivals = (rng.random(station.n_ports) < pressure) & available
                busy_until[arrivals] = tick + rng.integers(6, 19, size=int(arrivals.sum()))
                broken = int((repair_until > tick).sum())
                busy = int(((busy_until > tick) & (repair_until <= tick)).sum())
                records.append(
                    {
                        "station_id": station.station_id,
                        "scenario": scenario,
                        "ts": ts,
                        "ports_free": station.n_ports - busy - broken,
                        "ports_busy": busy,
                        "ports_broken": broken,
                    }
                )
    return stations, validate_status_frame(pd.DataFrame(records), stations)


def build_demo(directory: Path, seed: int = 42, days: int = 7) -> Path:
    stations, status = generate_fixture(seed, days)
    directory.mkdir(parents=True, exist_ok=True)
    station_file = directory / "stations.json"
    history_file = directory / "station_status.parquet"
    station_file.write_text(json.dumps([s.model_dump() for s in stations], indent=2))
    status.to_parquet(history_file, index=False)
    config = {
        "source": SOURCE,
        "seed": seed,
        "days": days,
        "data_type": "simulated",
        "horizons": [15, 30, 60],
        "step_minutes": 5,
        "queues": False,
    }
    (directory / "fixture_config.json").write_text(json.dumps(config, indent=2))
    labels = build_labels(status, [15, 30, 60])
    split = temporal_split(
        labels,
        train_end=START + pd.Timedelta(minutes=days * 288 * 5 * 0.6),
        calibration_end=START + pd.Timedelta(minutes=days * 288 * 5 * 0.8),
        max_horizon_minutes=60,
    )
    pipeline = train_candidate(
        split,
        TrainingConfig(random_state=seed, source=SOURCE),
        status_frame=status,
        stations=stations,
        seed=seed,
    )
    digest_builder = hashlib.sha256()
    for path in (station_file, history_file):
        payload = path.read_bytes()
        digest_builder.update(len(payload).to_bytes(8, "big"))
        digest_builder.update(payload)
    digest = digest_builder.hexdigest()
    manifest = save_pipeline(
        pipeline,
        directory / "model",
        data_version=SOURCE,
        fixture_hash=digest,
    )
    observed = START + pd.Timedelta(days=days - 1, hours=12)
    eta = observed + pd.Timedelta(minutes=30)
    request = {
        "station_id": "S001",
        "observed_at": observed.isoformat(),
        "eta": eta.isoformat(),
        "connector_type": "CCS2",
        "scenario": "normal",
    }
    (directory / "request.json").write_text(json.dumps(request, indent=2))
    with (directory / "prediction.json").open("w") as file, redirect_stdout(file):
        result = cli_main(
            [
                "predict",
                "--stations",
                str(station_file),
                "--status",
                str(history_file),
                "--model-dir",
                str(directory / "model"),
                "--station-id",
                "S001",
                "--observed-at",
                observed.isoformat(),
                "--eta",
                eta.isoformat(),
                "--connector-type",
                "CCS2",
                "--scenario",
                "normal",
                "--status-data-type",
                "simulated",
            ]
        )
    if result:
        raise ValueError("demo CLI inference failed")
    prediction = json.loads((directory / "prediction.json").read_text())
    report = [
        "# Synthetic Predictor integration demo",
        "",
        "Synthetic correlated per-port timers; no queues, routes or strategy evaluation.",
        "Not Bảo's simulator, partner data, or evidence of real-world accuracy.",
        "",
        f"Source/data version: {SOURCE}; seed: {seed}; days: {days}.",
        f"Model version: {manifest.model_version}; calibration: {manifest.calibration_method}.",
        f"Rows: {len(status)}; split counts: {manifest.sample_counts}.",
        f"Embargo: 60 minutes; split metadata: {manifest.split_metadata}.",
        "",
        "| Predictor | Brier ↓ | Log Loss ↓ | AUC ↑ | ECE ↓ | Samples |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, metric in pipeline.test_metrics.items():
        report.append(
            f"| {name} | {metric.brier_score:.6f} | {metric.log_loss:.6f} | "
            f"{metric.auc} | {metric.ece:.6f} | {metric.sample_count} |"
        )
    report += [
        "",
        "## Calibrated model reliability bins",
        "",
        "| Range | Count | Mean prediction | Observed rate |",
        "| --- | --- | --- | --- |",
    ]
    for bin_ in pipeline.test_metrics["lightgbm_calibrated"].calibration:
        closing = "]" if bin_.upper_bound == 1 else ")"
        report.append(
            f"| [{bin_.lower_bound}, {bin_.upper_bound}{closing} | {bin_.count} | "
            f"{bin_.mean_predicted} | {bin_.observed_rate} |"
        )
    report += [
        "",
        "## Example inference",
        "",
        "```json",
        json.dumps(prediction, indent=2),
        "```",
        "",
        "Scores describe this synthetic held-out timeline only; do not assume LightGBM wins.",
    ]
    (directory / "report.md").write_text("\n".join(report) + "\n")
    return directory / "model"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("app/backend/modules/prediction/artifacts/synthetic-demo"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    model = build_demo(args.output_dir, args.seed, args.days)
    print(json.dumps({"model_dir": str(model), "source": SOURCE, "data_type": "simulated"}))


if __name__ == "__main__":
    main()
