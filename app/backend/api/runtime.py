"""Public-module composition for calibrated prediction and stateful simulation.

Simulation inference sees background-only snapshots from the *same* bundle,
never the runner's private state or future observations. Driver state is separate.
"""

import json
from datetime import datetime, timedelta
from functools import lru_cache
from math import ceil
from pathlib import Path
from threading import Lock

import pandas as pd

from app.backend.contracts.enums import DataType, Scenario, Strategy
from app.backend.contracts.errors import DataSourceUnavailableError, ModelNotReadyError
from app.backend.contracts.ports import AllocationStrategy, Predictor, StationRepository
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import AllocationContext, RankedPlan, StatusWindow
from app.backend.contracts.simulation import (
    FixtureBundle,
    ScenarioConfig,
    SimulationRequest,
    SimulationResult,
)
from app.backend.contracts.stations import StationStatus
from app.backend.modules.prediction.public import load_predictor, read_manifest
from app.backend.modules.recommendation import (
    CandidateMetadata,
    RankingConfig,
    RecommendationAllocationStrategy,
)
from app.backend.modules.simulation.public import (
    AvailabilityFn,
    DefaultSimulationRunner,
    generate_status_history,
    strategy_for,
)
from app.backend.modules.station_data.public import (
    ScenarioSpec,
    generate_fixture_bundle,
    load_scenario_specs,
)


class RuntimePredictor:
    """Turn model integrity/inference failures into the existing typed API error."""

    def __init__(self, predictor: Predictor) -> None:
        self.predictor = predictor

    def predict(self, request: PredictRequest) -> PredictionResult:
        try:
            return self.predictor.predict(request)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            raise ModelNotReadyError(
                "model inference failed; check artifact and station metadata"
            ) from exc


class BackgroundStatusRepository:
    """Indexed immutable per-scenario snapshots; current is mandatory, past lags optional."""

    def __init__(
        self, frame: pd.DataFrame, stations: StationRepository, scenario: Scenario
    ) -> None:
        self.scenario = scenario
        self.stations = stations
        self.rows: dict[tuple[str, datetime], tuple[int, int, int]] = {}
        for station_id, ts, free, busy, broken, scenario_name in frame.loc[
            :, ["station_id", "ts", "ports_free", "ports_busy", "ports_broken", "scenario"]
        ].itertuples(index=False, name=None):
            if scenario_name != scenario.value:
                raise ValueError("background history scenario mismatch")
            key = (str(station_id), ts.to_pydatetime())
            if key in self.rows:
                raise ValueError("duplicate background snapshot")
            self.rows[key] = (int(free), int(busy), int(broken))

    def window(
        self, station_id: str, observed_at: datetime, lags: tuple[int, ...] = (15, 30, 60)
    ) -> StatusWindow:
        station = self.stations.get_station(station_id)
        if (
            observed_at.utcoffset() != timedelta(hours=7)
            or observed_at.minute % 5
            or observed_at.second
            or observed_at.microsecond
            or not lags
            or any(
                isinstance(lag, bool) or not isinstance(lag, int) or not 0 <= lag <= 60
                for lag in lags
            )
        ):
            raise ValueError("background window requires aligned +07 time and lags within 0..60")
        if (station_id, observed_at) not in self.rows:
            raise DataSourceUnavailableError("current background snapshot is unavailable")
        snapshots = []
        for lag in lags:
            ts = observed_at - timedelta(minutes=lag)
            counts = self.rows.get((station_id, ts))
            if counts is not None:
                snapshots.append(
                    StationStatus(
                        station_id=station_id,
                        ts=ts,
                        ports_free=counts[0],
                        ports_busy=counts[1],
                        ports_broken=counts[2],
                        n_ports=station.n_ports,
                        scenario=self.scenario,
                    )
                )
        return StatusWindow(
            station_id=station_id, observed_at=observed_at, lags=lags, statuses=tuple(snapshots)
        )


class SimulationAllocation:
    """Measured trip duration/capacity + independent per-run expected allocations."""

    def __init__(
        self,
        statuses: BackgroundStatusRepository,
        ranking: RankingConfig,
        model_version: str,
        duration: float,
        load: float,
    ) -> None:
        self.statuses = statuses
        self.ranking = ranking
        self.model_version = model_version
        self.duration = timedelta(minutes=duration)
        self.load = load
        self.reservations: list[tuple[str, datetime, datetime]] = []

    def select(self, context: AllocationContext) -> RankedPlan:
        metadata = {}
        loads = {}
        candidates = []
        observed = context.request.observed_at
        self.reservations = [item for item in self.reservations if item[2] > observed]
        for candidate in context.candidates:
            current = self.statuses.window(candidate.station_id, observed, (0,)).statuses[0]
            capacity = current.n_ports - current.ports_broken
            if capacity <= 0:
                continue
            minutes = (candidate.eta - context.request.depart_time).total_seconds() / 60
            bucket = observed + timedelta(
                minutes=max(5, ceil((candidate.eta - observed).total_seconds() / 300) * 5)
            )
            key = (context.request.scenario, candidate.station_id, bucket)
            candidates.append(candidate.model_copy(update={"eta": bucket}))
            metadata[key] = CandidateMetadata(travel_minutes=minutes, working_ports=capacity)
            loads[key] = self.load * sum(
                station == candidate.station_id and start <= bucket < end
                for station, start, end in self.reservations
            )
        strategy = RecommendationAllocationStrategy(
            ranking_config=self.ranking, metadata=metadata, virtual_loads=loads
        )
        plan = strategy.select(context.model_copy(update={"candidates": tuple(candidates)}))
        if plan.primary is not None:
            self.reservations.append(
                (plan.primary.station_id, plan.primary.eta, plan.primary.eta + self.duration)
            )
        return plan


class StatefulSimulation:
    """Fresh runner/strategy per request; bounded shared cache contains background data only."""

    def __init__(
        self,
        *,
        stations: StationRepository,
        model_dir: Path,
        generated_dir: Path,
        scenarios_path: Path,
        ranking: RankingConfig,
        maximum_horizon: int,
        duration: float,
        load: float,
    ) -> None:
        self.stations = stations
        self.model_dir = model_dir
        self.ranking = ranking
        self.maximum_horizon = maximum_horizon
        self.duration = duration
        self.load = load
        manifest = json.loads((generated_dir / "manifest.json").read_text())
        if manifest.get("data_type") != "simulated":
            raise ValueError("stateful simulation requires a simulated producer manifest")
        specs = load_scenario_specs(scenarios_path)
        self.specs: dict[Scenario, ScenarioSpec] = {}
        for scenario in Scenario:
            config = ScenarioConfig.model_validate(manifest["scenarios"][scenario.value]["config"])
            spec = specs[scenario].model_copy(
                update={"start": config.start, "end": config.end, "seed": config.seed}
            )
            if spec.to_config() != config:
                raise ValueError("scenario parameters do not match producer configuration")
            self.specs[scenario] = spec
        model_manifest = read_manifest(model_dir)
        if model_manifest.data_type != "simulated":
            raise ValueError("stateful demo requires a simulated model artifact")
        self.model_version = model_manifest.model_version
        self.model_checksum = model_manifest.binary_sha256
        self.lock = Lock()
        self.prepare = lru_cache(maxsize=4)(self._prepare)

    def _prepare(
        self, scenario: Scenario, seed: int, count: int
    ) -> tuple[FixtureBundle, ScenarioConfig, BackgroundStatusRepository, AvailabilityFn]:
        spec = self.specs[scenario].model_copy(update={"seed": seed})
        bundle = generate_fixture_bundle(spec, self.stations.list_stations(), count)
        config = spec.to_config()
        frame = generate_status_history(bundle, self.stations.list_stations(), config)
        statuses = BackgroundStatusRepository(frame, self.stations, scenario)
        try:
            manifest = read_manifest(self.model_dir)
            if (manifest.model_version, manifest.binary_sha256) != (
                self.model_version,
                self.model_checksum,
            ):
                raise ValueError(
                    "simulation artifact changed after startup; restart with an immutable release"
                )
            predictor = RuntimePredictor(
                load_predictor(
                    self.model_dir, statuses, self.stations, status_data_type=DataType.SIMULATED
                )
            )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ModelNotReadyError(
                "simulation model artifact is unavailable or incompatible"
            ) from exc

        @lru_cache(maxsize=8192)
        def availability(station_id: str, observed_at: datetime, eta: datetime) -> float:
            bucket = observed_at + timedelta(
                minutes=max(5, ceil((eta - observed_at).total_seconds() / 300) * 5)
            )
            result = predictor.predict(
                PredictRequest(
                    station_id=station_id,
                    observed_at=observed_at,
                    eta=bucket,
                    connector_type=self.stations.get_station(station_id).connector_types[0],
                    scenario=scenario,
                )
            )
            if result.model_version != self.model_version:
                raise ModelNotReadyError(
                    "simulation predictor version differs from the startup model"
                )
            return result.p_available

        return bundle, config, statuses, availability

    def run(self, request: SimulationRequest, strategy: AllocationStrategy) -> SimulationResult:
        del strategy  # Per-request enum selects a fresh real strategy, never the fake allocation.
        with self.lock:
            bundle, config, statuses, availability = self.prepare(
                request.scenario, request.seed, request.vehicle_count
            )
            runner = DefaultSimulationRunner(
                lambda _: bundle,
                self.stations.list_stations(),
                {request.scenario: config},
                availability=availability if request.strategy == Strategy.AI_ALLOCATION else None,
                min_soc_pct=self.ranking.min_arrival_soc_pct,
                max_prediction_horizon_minutes=self.maximum_horizon,
            )
            ai = SimulationAllocation(
                statuses, self.ranking, self.model_version, self.duration, self.load
            )
            selected = strategy_for(runner, request.strategy, ai_strategy=ai)
            result = runner.run(request, selected)
            if request.strategy != Strategy.AI_ALLOCATION:
                result = result.model_copy(update={"model_version": "simulated-baseline-v1"})
            return result
