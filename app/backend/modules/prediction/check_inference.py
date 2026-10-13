"""Run local integration acceptance cases against a trusted simulated artifact.

This verification CLI is not an API handler or a runtime repository adapter.
Fault fixtures are temporary; the input model/history remain unchanged.
"""

import argparse
import hashlib
import json
import sys
import tempfile
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import DataSourceUnavailableError, DomainError
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import StatusWindow
from app.backend.infrastructure.repositories import FileStationRepository, ParquetStatusRepository
from app.backend.modules.prediction.artifacts import read_manifest
from app.backend.modules.prediction.public import load_predictor


class _PartialWindow:
    """Acceptance-test fixture returning selected missing past/current snapshots."""

    def __init__(self, base: ParquetStatusRepository, omit: tuple[int, ...]) -> None:
        self.base = base
        self.omit = omit

    def window(
        self, station_id: str, observed_at: datetime, lags: tuple[int, ...] = (15, 30, 60)
    ) -> StatusWindow:
        window = self.base.window(station_id, observed_at, lags)
        omitted = {observed_at - timedelta(minutes=lag) for lag in self.omit}
        return window.model_copy(
            update={"statuses": tuple(s for s in window.statuses if s.ts not in omitted)}
        )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_cases(
    model_dir: Path,
    stations_path: Path,
    status_path: Path,
    observed_at: datetime,
    station_id: str = "S001",
) -> dict[str, Any]:
    """Return actual successes/errors plus acceptance verdicts, never HTTP claims."""
    manifest = read_manifest(model_dir)
    if manifest.data_type != "simulated":
        raise ValueError("acceptance fixture must be explicitly simulated")
    if manifest.split_metadata["max_horizon_minutes"] != 60:
        raise ValueError("acceptance matrix requires a model maximum horizon of exactly 60 minutes")
    stations = FileStationRepository(stations_path)
    station = stations.get_station(station_id)
    if station.connector_types != ["CCS2"]:
        raise ValueError("acceptance fixture requires a single CCS2 station")
    before = {
        "binary": _digest(model_dir / manifest.model_file),
        "manifest": _digest(model_dir / "manifest.json"),
        "stations": _digest(stations_path),
        "status": _digest(status_path),
    }
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="vev-inference-cases-") as temporary:
        scratch = Path(temporary)

        def record(
            case_id: str,
            layer: str,
            request: PredictRequest,
            action: Callable[[], object],
            expected_error: type[Exception] | None = None,
            message_part: str = "",
        ) -> None:
            entry: dict[str, Any] = {
                "case_id": case_id,
                "layer": layer,
                "request": request.model_dump(mode="json"),
                "expected": (
                    {"outcome": "prediction", "data_type": "simulated"}
                    if expected_error is None
                    else {
                        "outcome": "error",
                        "type": expected_error.__name__,
                        "message_contains": message_part,
                    }
                ),
            }
            try:
                actual = action()
                if isinstance(actual, PredictionResult):
                    entry["response"] = actual.model_dump(mode="json")
                    entry["passed"] = (
                        expected_error is None
                        and 0 <= actual.p_available <= 1
                        and actual.data_type == DataType.SIMULATED
                        and actual.model_version == manifest.model_version
                        and actual.station_id == request.station_id
                        and actual.eta == request.eta
                    )
                else:
                    entry["actual"] = "unexpected non-prediction return"
                    entry["passed"] = False
            except Exception as exc:  # Record failed acceptance cases; do not hide them.
                entry["error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc).replace(str(scratch), "<fault-fixture>")[:2000],
                }
                entry["passed"] = (
                    expected_error is not None
                    and isinstance(exc, expected_error)
                    and message_part in str(exc)
                )
            cases.append(entry)

        def request(scenario: Scenario, minutes: int) -> PredictRequest:
            return PredictRequest(
                station_id=station_id,
                observed_at=observed_at,
                eta=observed_at + timedelta(minutes=minutes),
                connector_type="CCS2",
                scenario=scenario,
            )

        for scenario in Scenario:
            repository = ParquetStatusRepository(status_path, stations, scenario)
            predictor = load_predictor(
                model_dir, repository, stations, status_data_type=DataType.SIMULATED
            )
            for horizon in (15, 30, 60):
                req = request(scenario, horizon)
                record(
                    f"valid_{scenario.value}_{horizon}",
                    "file_repository_and_predictor",
                    req,
                    lambda req=req, predictor=predictor: predictor.predict(req),
                )

        req = request(Scenario.NORMAL, 30)
        base = ParquetStatusRepository(status_path, stations, Scenario.NORMAL)
        complete = base.window(station_id, observed_at, (0, 15, 30, 60))
        for omitted in ((15,), (30,), (60,), (15, 30, 60), (0,)):
            suffix = "_".join(str(lag) for lag in omitted)
            partial_predictor = load_predictor(
                model_dir,
                _PartialWindow(base, omitted),
                stations,
                status_data_type=DataType.SIMULATED,
            )
            record(
                f"partial_window_missing_{suffix}",
                "predictor_with_partial_window_fixture",
                req,
                lambda predictor=partial_predictor: predictor.predict(req),
                ValueError if omitted == (0,) else None,
                "exactly one current status" if omitted == (0,) else "",
            )

        for omitted in (15, 30, 60, 0):
            rows = [
                {
                    "station_id": s.station_id,
                    "ts": s.ts,
                    "ports_free": s.ports_free,
                    "ports_busy": s.ports_busy,
                    "ports_broken": s.ports_broken,
                    "scenario": s.scenario.value,
                }
                for s in complete.statuses
                if s.ts != observed_at - timedelta(minutes=omitted)
            ]
            fault_history = scratch / f"missing-{omitted}.parquet"
            pd.DataFrame(rows).to_parquet(fault_history, index=False)
            strict_predictor = load_predictor(
                model_dir,
                ParquetStatusRepository(fault_history, stations, Scenario.NORMAL),
                stations,
                status_data_type=DataType.SIMULATED,
            )
            record(
                f"file_repository_missing_{omitted}",
                "strict_file_repository",
                req,
                lambda predictor=strict_predictor: predictor.predict(req),
                DataSourceUnavailableError,
                "missing status snapshots",
            )

        predictor = load_predictor(model_dir, base, stations, status_data_type=DataType.SIMULATED)
        for horizon in (65, 32):
            invalid = request(Scenario.NORMAL, horizon)
            record(
                f"invalid_horizon_{horizon}",
                "predictor_request_validation",
                invalid,
                lambda invalid=invalid: predictor.predict(invalid),
                ValueError,
                "positive five-minute multiple <= 60 minutes",
            )

        for failure in ("missing_manifest", "missing_binary", "bad_checksum", "invalid_manifest"):
            fault_model = scratch / failure
            fault_model.mkdir()
            if failure != "missing_manifest":
                (fault_model / "manifest.json").write_text(
                    "{}"
                    if failure == "invalid_manifest"
                    else (model_dir / "manifest.json").read_text()
                )
            if failure == "bad_checksum":
                (fault_model / manifest.model_file).write_bytes(
                    (model_dir / manifest.model_file).read_bytes() + b"acceptance-test-corruption"
                )
            record(
                f"artifact_{failure}",
                "artifact_loader",
                req,
                lambda directory=fault_model: load_predictor(
                    directory, base, stations, status_data_type=DataType.SIMULATED
                ),
                FileNotFoundError if failure.startswith("missing") else ValueError,
                {
                    "missing_manifest": "manifest.json",
                    "missing_binary": "missing model artifact",
                    "bad_checksum": "SHA-256 checksum mismatch",
                    "invalid_manifest": "invalid model manifest",
                }[failure],
            )
    unchanged = before == {
        "binary": _digest(model_dir / manifest.model_file),
        "manifest": _digest(model_dir / "manifest.json"),
        "stations": _digest(stations_path),
        "status": _digest(status_path),
    }
    return {
        "model_version": manifest.model_version,
        "source": manifest.source,
        "data_type": manifest.data_type,
        "observed_at": observed_at.isoformat(),
        "case_count": len(cases),
        "passed_count": sum(case["passed"] for case in cases),
        "inputs_unchanged": unchanged,
        "passed": unchanged and all(case["passed"] for case in cases),
        "scope": "Local inference/loader checks; no HTTP mapping or real-world accuracy claim",
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--stations", required=True, type=Path)
    parser.add_argument("--status", required=True, type=Path)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--station-id", default="S001")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        if output.is_relative_to(args.model_dir.resolve()) or output in {
            args.stations.resolve(),
            args.status.resolve(),
        }:
            raise ValueError("output must not overwrite model or input data")
        report = run_cases(
            args.model_dir,
            args.stations,
            args.status,
            datetime.fromisoformat(args.observed_at),
            args.station_id,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError, DomainError) as exc:
        print(f"Inference acceptance setup failed: {exc}", file=sys.stderr)
        return 2
    print(f"{report['passed_count']}/{report['case_count']} cases passed; {args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
