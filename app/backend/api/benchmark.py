"""Repeat paired simulated comparisons across seeds using an immutable release.

Usage: python -m app.backend.api.benchmark --release-dir PATH --output PATH
No HTTP/Goong calls, model fitting, Driver allocation or production traffic.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

from app.backend.api.runtime import StatefulSimulation
from app.backend.contracts.enums import Scenario, Strategy
from app.backend.contracts.simulation import SimulationRequest, WhatIfRequest
from app.backend.infrastructure.repositories.files import FileStationRepository
from app.backend.infrastructure.services.fakes import FakeAllocationStrategy
from app.backend.modules.prediction.public import read_manifest
from app.backend.modules.recommendation import RankingConfig


def summarize(values: list[float]) -> dict[str, float | int]:
    return {
        "mean": mean(values),
        "sample_std": stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "n": len(values),
    }


def benchmark(
    runner: StatefulSimulation, seeds: list[int], count: int, with_whatif: bool = False
) -> dict:
    if (
        not seeds
        or len(set(seeds)) != len(seeds)
        or any(isinstance(seed, bool) or seed < 0 for seed in seeds)
        or count <= 0
    ):
        raise ValueError("benchmark requires distinct nonnegative seeds and a positive population")
    runs, changes = [], []
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    paired: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for scenario in Scenario:
        for seed in seeds:
            cases = {}
            for strategy in Strategy:
                request = SimulationRequest(
                    scenario=scenario, seed=seed, vehicle_count=count, strategy=strategy
                )
                result = runner.run(request, FakeAllocationStrategy())
                runs.append(result.model_dump(mode="json"))
                cases[strategy] = result
                for metric, value in result.metrics.model_dump().items():
                    grouped[f"{scenario.value}/{strategy.value}"][metric].append(float(value))
            if len({result.fixture_hash for result in cases.values()}) != 1:
                raise ValueError("strategy fixture identity mismatch")
            ai = cases[Strategy.AI_ALLOCATION].metrics
            for baseline in (Strategy.NEAREST, Strategy.CURRENTLY_AVAILABLE):
                base = cases[baseline].metrics
                for metric in (
                    "success_rate",
                    "mean_wait_minutes",
                    "mean_detour_km",
                    "failed_count",
                ):
                    paired[f"{scenario.value}/ai_minus_{baseline.value}"][metric].append(
                        float(getattr(ai, metric) - getattr(base, metric))
                    )
            if with_whatif:
                for change in (
                    {"kind": "add_ports", "station_id": "S001", "ports": 2},
                    {"kind": "shift_departures", "fraction": 0.2, "target_hour": 21},
                ):
                    result = runner.run_whatif(
                        WhatIfRequest.model_validate(
                            {
                                "scenario": scenario,
                                "seed": seed,
                                "vehicle_count": count,
                                "strategy": Strategy.AI_ALLOCATION,
                                "change": change,
                            }
                        )
                    )
                    changes.append(result.model_dump(mode="json"))
    return {
        "data_type": "simulated",
        "seeds": seeds,
        "vehicle_count_per_run": count,
        "model_version": runner.model_version,
        "model_sha256": runner.model_checksum,
        "summary": {
            key: {metric: summarize(values) for metric, values in metrics.items()}
            for key, metrics in grouped.items()
        },
        "paired_deltas": {
            key: {metric: summarize(values) for metric, values in metrics.items()}
            for key, metrics in paired.items()
        },
        "runs": runs,
        "whatif_runs": changes,
        "assumptions": [
            "success_rate means free port on arrival, not served after waiting",
            "AI sees background snapshots, currently_available sees foreground too",
            "simulator distances/speeds are assumptions, not Goong traffic",
            "multiple seeds in the same simulator family are not real-world validation",
            "capacity what-if uses frozen model unless an explicit matched variant is configured",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capacity-models-dir", type=Path)
    parser.add_argument("--seeds", default="42,43,44,45,46")
    parser.add_argument("--vehicles", type=int, default=100)
    parser.add_argument("--whatif", action="store_true")
    args = parser.parse_args()
    seeds = [int(value) for value in args.seeds.split(",")]
    release = args.release_dir.resolve()
    manifest = read_manifest(release / "model")
    runner = StatefulSimulation(
        stations=FileStationRepository(release / "data/stations.json"),
        model_dir=release / "model",
        generated_dir=release / "data",
        scenarios_path=release / "producer_scenarios.yaml",
        ranking=RankingConfig(),
        maximum_horizon=int(manifest.split_metadata["max_horizon_minutes"]),
        duration=60,
        load=1,
        capacity_models_dir=args.capacity_models_dir,
    )
    report = benchmark(runner, seeds, args.vehicles, args.whatif)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    print(
        json.dumps(
            {
                "output": str(args.output),
                "runs": len(report["runs"]),
                "whatif_runs": len(report["whatif_runs"]),
                "model_version": runner.model_version,
            }
        )
    )


if __name__ == "__main__":
    main()
