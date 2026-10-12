"""Simulation commands: ``history`` and ``compare``.

Both read the output of ``app.backend.modules.station_data.cli generate``
(stations, ``manifest.json``, per-scenario fixture bundles) as files validated
by shared contracts. ``history`` replays each bundle and writes
``station_status.parquet``. ``compare`` runs the strategies on the bundle's
last day and writes ``compare_results.json``; ``ai_allocation`` runs only when
``--ai-strategy package.module:attribute`` names an injected strategy (an
object with ``select``, or a zero-argument factory returning one).
"""

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from app.backend.contracts.enums import Scenario, Strategy
from app.backend.contracts.ports import AllocationStrategy
from app.backend.contracts.simulation import (
    FixtureBundle,
    ScenarioConfig,
    SimulationRequest,
    SimulationResult,
)
from app.backend.contracts.stations import Station
from app.backend.modules.simulation.history import generate_status_history, write_status_history
from app.backend.modules.simulation.runner import DefaultSimulationRunner, bundle_hash

STATUS_FILE = "station_status.parquet"
MANIFEST_FILE = "manifest.json"
BUNDLE_FILE = "fixture_bundle.json"
RESULTS_FILE = "compare_results.json"


def _read_inputs(input_dir: Path) -> tuple[dict[str, Any], tuple[Station, ...]]:
    manifest_path = input_dir / MANIFEST_FILE
    if not manifest_path.exists():
        raise ValueError(f"{manifest_path} not found; run station_data.cli generate first")
    summary = json.loads(manifest_path.read_text(encoding="utf-8"))
    stations = tuple(
        Station.model_validate(row)
        for row in json.loads((input_dir / "stations.json").read_text(encoding="utf-8"))
    )
    return summary, stations


def _read_bundle(input_dir: Path, name: str, entry: dict[str, Any]) -> FixtureBundle:
    path = input_dir / name / BUNDLE_FILE
    bundle = FixtureBundle.model_validate_json(path.read_text(encoding="utf-8"))
    if bundle_hash(bundle) != entry["fixture_hash"]:
        raise ValueError(f"fixture hash mismatch for scenario {name}")
    return bundle


def build_history(input_dir: Path, output_dir: Path) -> dict[str, object]:
    summary, stations = _read_inputs(input_dir)
    frames: list[pd.DataFrame] = []
    for name, entry in summary["scenarios"].items():
        config = ScenarioConfig.model_validate(entry["config"])
        bundle = _read_bundle(input_dir, name, entry)
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


def _load_ai_strategy(spec: str) -> AllocationStrategy:
    module_name, _, attribute = spec.partition(":")
    if not module_name or not attribute:
        raise ValueError("--ai-strategy must look like package.module:attribute")
    target = getattr(importlib.import_module(module_name), attribute)
    return target() if isinstance(target, type) or not hasattr(target, "select") else target


def compare(
    input_dir: Path,
    scenarios: list[Scenario],
    vehicles: int,
    ai_strategy: str | None,
) -> list[SimulationResult]:
    summary, stations = _read_inputs(input_dir)
    selected = {
        name: entry for name, entry in summary["scenarios"].items() if Scenario(name) in scenarios
    }
    if not selected:
        raise ValueError("no matching scenario in manifest")
    results: list[SimulationResult] = []
    for name, entry in selected.items():
        config = ScenarioConfig.model_validate(entry["config"])
        bundle = _read_bundle(input_dir, name, entry)
        runner = DefaultSimulationRunner(
            lambda _request, b=bundle: b, stations, {config.scenario: config}
        )
        strategies = runner.baseline_strategies()
        if ai_strategy:
            strategies[Strategy.AI_ALLOCATION] = _load_ai_strategy(ai_strategy)
        request = SimulationRequest(
            scenario=config.scenario,
            seed=config.seed,
            vehicle_count=vehicles,
            strategy=Strategy.NEAREST,
        )
        results.extend(runner.compare(request, strategies))
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simulation.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    history = commands.add_parser("history", help="write station_status.parquet from fixtures")
    history.add_argument("--input", type=Path, required=True, help="station_data.cli output dir")
    history.add_argument("--output", type=Path, default=None, help="default: same as --input")
    cmp = commands.add_parser("compare", help="compare strategies on fixture bundles")
    cmp.add_argument("--input", type=Path, required=True, help="station_data.cli output dir")
    cmp.add_argument("--scenario", choices=[*(s.value for s in Scenario), "all"], default="normal")
    cmp.add_argument("--vehicles", type=int, default=100)
    cmp.add_argument("--ai-strategy", default=None, help="package.module:attribute")
    cmp.add_argument("--output", type=Path, default=None, help="default: --input")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "history":
            summary = build_history(args.input, args.output or args.input)
            print((args.output or args.input) / MANIFEST_FILE)
            print(json.dumps(summary["status_history"]))
            return 0
        scenarios = list(Scenario) if args.scenario == "all" else [Scenario(args.scenario)]
        results = compare(args.input, scenarios, args.vehicles, args.ai_strategy)
        output = args.output or args.input
        output.mkdir(parents=True, exist_ok=True)
        payload = json.dumps([json.loads(item.model_dump_json()) for item in results], indent=2)
        (output / RESULTS_FILE).write_text(payload, encoding="utf-8")
    except (ValueError, OSError, KeyError, ImportError, AttributeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(output / RESULTS_FILE)
    print(_table(results))
    return 0


def _table(results: list[SimulationResult]) -> str:
    header = (
        f"{'scenario':<13}{'strategy':<20}{'success':>8}"
        f"{'detour_km':>10}{'wait_min':>9}{'failed':>7}"
    )
    rows = [
        f"{r.scenario.value:<13}{r.strategy.value:<20}{r.metrics.success_rate:>8.2f}"
        f"{r.metrics.mean_detour_km:>10.2f}{r.metrics.mean_wait_minutes:>9.2f}"
        f"{r.metrics.failed_count:>4}/{r.metrics.vehicle_count}"
        for r in results
    ]
    hashes = sorted({f"{r.scenario.value}: {r.fixture_hash}" for r in results})
    return "\n".join([header, *rows, "fixture_hash", *hashes])


if __name__ == "__main__":
    raise SystemExit(main())
