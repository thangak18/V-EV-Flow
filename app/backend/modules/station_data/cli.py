"""Generate stations, scenario configs and fixture bundles.

``python -m app.backend.modules.station_data.cli generate``. Status history is
added by ``app.backend.modules.simulation.cli history`` (domains cannot import
each other; the shared interface is the files and contract models).
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.backend.contracts.enums import DataType, Scenario
from app.backend.modules.station_data.generator import generate_fixture_bundle
from app.backend.modules.station_data.loaders import (
    SCENARIOS_PATH,
    STATIONS_PATH,
    load_scenario_specs,
    load_stations,
)
from app.backend.modules.station_data.manifests import DATA_VERSION, write_fixture_bundle

DEFAULT_OUTPUT = Path(__file__).parent / "generated"
MANIFEST_FILE = "manifest.json"


def generate(
    scenarios: list[Scenario],
    seed: int,
    history_days: int | None,
    vehicle_count: int,
    output: Path,
    history_end: datetime | None = None,
    stations_path: Path = STATIONS_PATH,
    scenarios_path: Path = SCENARIOS_PATH,
) -> dict[str, object]:
    stations = load_stations(stations_path)
    specs = load_scenario_specs(scenarios_path)
    output.mkdir(parents=True, exist_ok=True)
    # Shared calendar window by default so a global temporal split sees every scenario.
    common_end = history_end or specs[Scenario.NORMAL].end
    manifests: dict[str, object] = {}
    for scenario in scenarios:
        spec = specs[scenario].model_copy(update={"seed": seed})
        window = spec.history_spec(history_days, common_end)
        bundle = generate_fixture_bundle(window, stations, vehicle_count)
        manifest = write_fixture_bundle(bundle, output / scenario.value)
        manifests[scenario.value] = json.loads(manifest.model_dump_json()) | {
            "history_days": window.history_days,
            "config": json.loads(window.to_config().model_dump_json()),
        }
    (output / "stations.json").write_text(
        stations_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    summary: dict[str, object] = {
        "data_version": DATA_VERSION,
        "data_type": DataType.SIMULATED.value,
        "seed": seed,
        "generated_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "station_count": len(stations),
        "scenarios": manifests,
    }
    (output / MANIFEST_FILE).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_history_end(value: str) -> datetime:
    """Accept an ISO time or ``today`` (23:55 of the current +07:00 calendar day)."""
    if value == "today":
        now = datetime.now(timezone(timedelta(hours=7)))
        return now.replace(hour=23, minute=55, second=0, microsecond=0)
    return datetime.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="station_data.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    gen = commands.add_parser("generate", help="write stations, fixture bundles and manifests")
    gen.add_argument("--scenario", choices=[*(s.value for s in Scenario), "all"], default="all")
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--history-days", type=int, default=None, help="default: scenarios.yaml")
    gen.add_argument(
        "--history-end",
        type=parse_history_end,
        default=None,
        help="ISO time with +07:00, or 'today', ending every scenario's history; "
        "default: normal scenario end",
    )
    gen.add_argument("--vehicles", type=int, default=100)
    gen.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scenarios = list(Scenario) if args.scenario == "all" else [Scenario(args.scenario)]
    try:
        summary = generate(
            scenarios, args.seed, args.history_days, args.vehicles, args.output, args.history_end
        )
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(args.output / MANIFEST_FILE)
    print(json.dumps({"scenarios": list(summary["scenarios"])}))  # type: ignore[call-overload]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
