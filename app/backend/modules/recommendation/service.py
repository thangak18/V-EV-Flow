"""Application service for primary and reachable backup recommendations."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from math import ceil
from typing import Protocol

from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import DataSourceUnavailableError
from app.backend.contracts.ports import (
    Predictor,
    RouteProvider,
    StationRepository,
    StatusRepository,
)
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import (
    FeasibleCandidate,
    Plan,
    RecommendationRequest,
    RecommendationResult,
    RouteRequest,
    RouteResult,
    StatusWindow,
    Vehicle,
)
from app.backend.contracts.stations import Station, StationStatus
from app.backend.modules.recommendation.ranking import RankingConfig, RankingInput, rank_candidates
from app.backend.modules.recommendation.soc import (
    FeasibleRouteCandidate,
    RejectionReason,
    RouteCandidate,
    evaluate_feasibility,
    working_ports,
)


class VirtualLoadReader(Protocol):
    """Read-only expected-demand snapshots; absent station means zero demand."""

    async def snapshot(self, at: datetime, scenario: Scenario) -> Mapping[str, float]: ...


class RecommendationService:
    """Compose routing, C3 feasibility, prediction, and C4 ranking.

    ``data_type`` explicitly labels the injected non-model sources. Model
    evidence is combined with that label; different source types yield mixed.
    Primary/backup predictions must share model, contract and provenance.
    Plan ETA is the conservative prediction bucket, not physical arrival.
    Detour is max(0, routed itinerary distance minus direct-road distance).
    Only an empty route tuple establishes a recoverable missing edge. The
    frozen RouteUnavailableError does not distinguish no-route from outages.
    Horizon limits are injected per scenario from the same trained artifact's
    split_metadata.max_horizon_minutes used by its predictor. The shared port
    exposes no capability metadata; composition must keep those values in sync.
    A known out-of-horizon candidate is excluded before inference; unexpected
    predictor failures, including inconsistent capability configuration, raise.
    """

    def __init__(
        self,
        *,
        station_repository: StationRepository,
        status_repositories: Mapping[Scenario, StatusRepository],
        route_provider: RouteProvider,
        predictors: Mapping[Scenario, Predictor],
        ranking_config: RankingConfig,
        minimum_arrival_soc_pct: float | None = None,
        data_type: DataType,
        max_prediction_horizon_minutes: Mapping[Scenario, int],
        allocation_method: str = "heuristic_ranking",
        virtual_load_provider: VirtualLoadReader | None = None,
    ) -> None:
        self._stations = station_repository
        self._statuses = {Scenario(key): value for key, value in status_repositories.items()}
        self._routes = route_provider
        self._predictors = {Scenario(key): value for key, value in predictors.items()}
        self._horizons = {
            Scenario(key): value for key, value in max_prediction_horizon_minutes.items()
        }
        if self._horizons.keys() != self._predictors.keys():
            raise ValueError("prediction horizon configuration must match predictor scenarios")
        for maximum in self._horizons.values():
            if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum <= 0:
                raise ValueError("maximum prediction horizon must be a positive integer in minutes")
        self._ranking = ranking_config
        threshold = (
            ranking_config.min_arrival_soc_pct
            if minimum_arrival_soc_pct is None
            else minimum_arrival_soc_pct
        )
        if threshold != ranking_config.min_arrival_soc_pct:
            raise ValueError("C3 and C4 must use the same minimum arrival SOC")
        self._minimum_soc = threshold
        if not allocation_method:
            raise ValueError("allocation_method must be nonempty")
        self._data_type = DataType(data_type)
        self._allocation_method = allocation_method
        self._virtual_loads = virtual_load_provider

    async def recommend(self, request: RecommendationRequest) -> RecommendationResult:
        request = RecommendationRequest.model_validate(request.model_dump())
        self._validate_times(request)
        if request.depart_time < request.observed_at:
            raise ValueError("depart_time must not precede observed_at")
        statuses = self._scenario_dependency(self._statuses, request.scenario, "status")
        predictor = self._scenario_dependency(self._predictors, request.scenario, "predictor")
        stations = tuple(sorted(self._stations.list_stations(), key=lambda item: item.station_id))
        if not stations:
            return self._empty_result(
                request, reasons=["No charging stations were available in the dataset."]
            )

        direct = self._shortest_route(
            await self._route(
                request.origin,
                request.destination,
                request.depart_time,
                request.vehicle,
            )
        )
        if direct is None:
            return self._empty_result(request, reasons=["No direct road route was available."])

        primary_candidates = []
        predictions: dict[str, PredictionResult] = {}
        feasible_primary: dict[str, FeasibleRouteCandidate] = {}
        station_statuses: dict[str, StationStatus] = {}
        primary_outcomes: set[str] = set()
        for station in stations:
            status = self._current_status(statuses, station, request)
            station_statuses[station.station_id] = status
            routes = await self._route(
                request.origin,
                self._coordinate(station),
                request.depart_time,
                request.vehicle,
            )
            if not routes:
                primary_outcomes.add("no_station_route")
                continue
            feasible_routes = []
            for route in routes:
                physical_eta = request.depart_time + timedelta(minutes=route.duration_minutes)
                candidate = RouteCandidate(
                    station=station,
                    status=status,
                    route=route,
                    eta=physical_eta,
                    detour_km=0.0,
                )
                evaluation = evaluate_feasibility(request.vehicle, (candidate,), self._minimum_soc)
                feasible_routes.extend(evaluation.accepted)
                primary_outcomes.update(item.reason.value for item in evaluation.rejected)
            if not feasible_routes:
                continue
            chosen = min(
                feasible_routes,
                key=lambda item: (
                    item.candidate.route.duration_minutes,
                    item.candidate.route.distance_km,
                ),
            )
            if not self._prediction_supported(request, chosen):
                primary_outcomes.add("unsupported_prediction_horizon")
                continue
            onward = self._shortest_route(
                await self._route(
                    self._coordinate(station),
                    request.destination,
                    chosen.candidate.eta,
                    request.vehicle,
                )
            )
            if onward is None:
                primary_outcomes.add("no_destination_route")
                continue
            chosen = self._with_detour(
                chosen,
                max(
                    0.0,
                    chosen.candidate.route.distance_km + onward.distance_km - direct.distance_km,
                ),
            )
            predicted = self._predict(request, predictor, chosen, request.scenario)
            predictions[station.station_id] = predicted
            feasible_primary[station.station_id] = chosen
            primary_candidates.append(
                self._ranking_input(chosen, predicted, working_ports(station, status))
            )

        ranked = rank_candidates(
            primary_candidates,
            self._ranking,
            await self._candidate_loads(primary_candidates, request.scenario),
        )
        if not ranked:
            return self._empty_result(
                request,
                reasons=self._outcome_reasons(primary_outcomes),
            )
        primary = ranked[0]
        primary_station = self._stations.get_station(primary.station_id)
        primary_journey = feasible_primary[primary.station_id].candidate
        primary_physical_eta = primary_journey.eta
        backup_inputs = []
        backup_outcomes: set[str] = set()
        for station in stations:
            if station.station_id == primary.station_id:
                continue
            if station.station_id not in station_statuses:
                continue
            legs = await self._route(
                self._coordinate(primary_station),
                self._coordinate(station),
                primary_physical_eta,
                request.vehicle,
            )
            if not legs:
                backup_outcomes.add("no_station_route")
                continue
            feasible_routes = []
            for leg in legs:
                cumulative_distance = primary.distance_km + leg.distance_km
                cumulative_route = RouteResult(
                    distance_km=cumulative_distance,
                    duration_minutes=(
                        primary_journey.route.duration_minutes + leg.duration_minutes
                    ),
                    geometry=None,
                    source=f"cumulative:{primary_journey.route.source}+{leg.source}",
                )
                physical_eta = primary_physical_eta + timedelta(minutes=leg.duration_minutes)
                candidate = RouteCandidate(
                    station=station,
                    status=station_statuses[station.station_id],
                    route=cumulative_route,
                    eta=physical_eta,
                    detour_km=0.0,
                )
                evaluation = evaluate_feasibility(request.vehicle, (candidate,), self._minimum_soc)
                feasible_routes.extend(evaluation.accepted)
                backup_outcomes.update(item.reason.value for item in evaluation.rejected)
            if not feasible_routes:
                continue
            chosen = min(
                feasible_routes,
                key=lambda item: (
                    item.candidate.route.duration_minutes,
                    item.candidate.route.distance_km,
                ),
            )
            if not self._prediction_supported(request, chosen):
                backup_outcomes.add("unsupported_prediction_horizon")
                continue
            onward = self._shortest_route(
                await self._route(
                    self._coordinate(station),
                    request.destination,
                    chosen.candidate.eta,
                    request.vehicle,
                )
            )
            if onward is None:
                backup_outcomes.add("no_destination_route")
                continue
            chosen = self._with_detour(
                chosen,
                max(
                    0.0,
                    chosen.candidate.route.distance_km + onward.distance_km - direct.distance_km,
                ),
            )
            predicted = self._predict(request, predictor, chosen, request.scenario)
            predictions[station.station_id] = predicted
            backup_inputs.append(
                self._ranking_input(
                    chosen,
                    predicted,
                    working_ports(station, station_statuses[station.station_id]),
                )
            )

        ranked_backups = rank_candidates(
            backup_inputs,
            self._ranking,
            await self._candidate_loads(backup_inputs, request.scenario),
        )
        backup = ranked_backups[0] if ranked_backups else None
        primary_plan = self._plan(primary)
        backup_plan = self._plan(backup) if backup is not None else None
        primary_probability = primary.p_available
        plan_probability = primary_probability
        assumption = None
        reasons = [
            "Primary selected by configurable heuristic ranking after C3 feasibility.",
            "Plan ETA is a five-minute prediction bucket, not an exact physical arrival.",
        ]
        if backup is not None:
            plan_probability = 1 - (1 - primary_probability) * (1 - backup.p_available)
            assumption = "independent_stations"
            reasons.extend(
                [
                    "Backup reachability uses cumulative distance without charging at primary.",
                    "Backup ETA and probability were recomputed for the fallback journey.",
                    "Plan probability assumes independent stations, not guaranteed charging.",
                ]
            )
        else:
            reasons.append("No reachable/eligible backup was found.")
            reasons.extend(self._outcome_reasons(backup_outcomes))
        model_versions = {predictions[primary.station_id].model_version}
        if backup is not None:
            model_versions.add(predictions[backup.station_id].model_version)
        if len(model_versions) != 1:
            raise DataSourceUnavailableError(
                "primary and backup predictions use inconsistent model versions"
            )
        selected_data_types = {predictions[primary.station_id].data_type}
        if backup is not None:
            selected_data_types.add(predictions[backup.station_id].data_type)
        if len(selected_data_types) != 1:
            raise DataSourceUnavailableError(
                "primary and backup predictions use incompatible data provenance"
            )
        selected_data_types.add(self._data_type)
        result_data_type = (
            next(iter(selected_data_types)) if len(selected_data_types) == 1 else DataType.MIXED
        )
        return RecommendationResult(
            request_id=request.request_id,
            primary=primary_plan,
            backup=backup_plan,
            plan_p=plan_probability,
            plan_p_assumption=assumption,
            reasons=reasons,
            time_shift=None,
            model_version=next(iter(model_versions)),
            allocation_method=self._allocation_method,
            data_type=result_data_type,
        )

    async def _candidate_loads(
        self,
        candidates: list[RankingInput],
        scenario: Scenario,
    ) -> dict[str, float]:
        if self._virtual_loads is None:
            return {}
        snapshots: dict[datetime, Mapping[str, float]] = {}
        loads = {}
        for item in candidates:
            candidate = item.candidate
            if candidate.eta not in snapshots:
                snapshots[candidate.eta] = await self._virtual_loads.snapshot(
                    candidate.eta, scenario
                )
            loads[candidate.station_id] = snapshots[candidate.eta].get(candidate.station_id, 0.0)
        return loads

    async def _route(
        self,
        origin: Coordinate,
        destination: Coordinate,
        depart_time: datetime,
        vehicle: Vehicle,
    ) -> tuple[RouteResult, ...]:
        routes = await self._routes.get_routes(
            RouteRequest(
                origin=origin,
                destination=destination,
                depart_time=depart_time,
                vehicle=vehicle,
            )
        )
        if not isinstance(routes, tuple) or any(
            not isinstance(route, RouteResult) for route in routes
        ):
            raise ValueError("route provider must return a tuple of RouteResult")
        return tuple(RouteResult.model_validate(route.model_dump()) for route in routes)

    @staticmethod
    def _coordinate(station: Station) -> Coordinate:
        return Coordinate(lat=station.lat, lng=station.lng)

    @staticmethod
    def _validate_times(request: RecommendationRequest) -> None:
        observed = request.observed_at
        if observed.utcoffset() != timedelta(hours=7):
            raise ValueError("observed_at must use +07:00")
        if observed.minute % 5 or observed.second or observed.microsecond:
            raise ValueError("observed_at must align to five-minute buckets")
        if request.depart_time.utcoffset() != timedelta(hours=7):
            raise ValueError("depart_time must use +07:00")

    @staticmethod
    def _outcome_reasons(outcomes: set[str]) -> list[str]:
        descriptions = {
            "no_station_route": "No station-specific road route was available for some candidates.",
            "no_destination_route": "No onward road route was available to measure journey detour.",
            RejectionReason.CONNECTOR_INCOMPATIBLE.value: "Charging connector was incompatible.",
            RejectionReason.CONNECTOR_CAPACITY_UNKNOWN.value: "Connector capacity was unknown.",
            RejectionReason.NO_WORKING_PORTS.value: "No working charging capacity was available.",
            RejectionReason.INSUFFICIENT_ARRIVAL_SOC.value: "Arrival SOC was insufficient.",
            "unsupported_prediction_horizon": "Prediction ETA exceeded the model horizon.",
        }
        return [descriptions[key] for key in sorted(outcomes)]

    @staticmethod
    def _shortest_route(routes: tuple[RouteResult, ...]) -> RouteResult | None:
        if not routes:
            return None
        return min(routes, key=lambda item: (item.duration_minutes, item.distance_km))

    @staticmethod
    def _scenario_dependency(mapping, scenario: Scenario, label: str):
        try:
            return mapping[scenario]
        except KeyError as exc:
            raise ValueError(
                f"no {label} dependency configured for scenario {scenario.value}"
            ) from exc

    @staticmethod
    def _current_status(
        repository: StatusRepository, station: Station, request: RecommendationRequest
    ) -> StationStatus:
        window: StatusWindow = repository.window(station.station_id, request.observed_at, lags=(0,))
        if window.station_id != station.station_id or window.observed_at != request.observed_at:
            raise ValueError("status window does not match station and observed_at")
        matches = [item for item in window.statuses if item.ts == request.observed_at]
        if len(matches) != 1:
            raise ValueError("status window must contain exactly one current status")
        for item in window.statuses:
            if item.station_id != station.station_id:
                raise ValueError("status window contains another station")
            if item.scenario != request.scenario:
                raise ValueError("status window contains another scenario")
            if item.ts > request.observed_at:
                raise ValueError("future status snapshot after observed_at is forbidden")
            if item.n_ports != station.n_ports:
                raise ValueError("status capacity does not match station metadata")
        current = matches[0]
        return current

    def _prediction_supported(
        self, request: RecommendationRequest, feasible: FeasibleRouteCandidate
    ) -> bool:
        eta = self._prediction_bucket(request.observed_at, feasible.candidate.eta)
        horizon_seconds = (eta - request.observed_at).total_seconds()
        return 0 < horizon_seconds <= self._horizons[request.scenario] * 60

    def _predict(self, request, predictor, feasible, scenario) -> PredictionResult:
        prediction_eta = self._prediction_bucket(request.observed_at, feasible.candidate.eta)
        prediction_request = PredictRequest(
            station_id=feasible.candidate.station.station_id,
            observed_at=request.observed_at,
            eta=prediction_eta,
            connector_type=request.vehicle.connector_type,
            scenario=scenario,
        )
        response = predictor.predict(prediction_request)
        if not isinstance(response, PredictionResult):
            raise DataSourceUnavailableError("predictor must return a PredictionResult")
        try:
            result = PredictionResult.model_validate(response.model_dump(warnings=False))
        except ValueError as exc:
            raise DataSourceUnavailableError("predictor returned an invalid response") from exc
        if result.contract_version != RecommendationResult.model_fields["contract_version"].default:
            raise DataSourceUnavailableError(
                "prediction contract version is incompatible with recommendation"
            )
        if (
            result.station_id != prediction_request.station_id
            or result.eta != prediction_request.eta
        ):
            raise DataSourceUnavailableError(
                "predictor returned a station or ETA different from the request"
            )
        return result

    @staticmethod
    def _prediction_bucket(observed_at: datetime, physical_eta: datetime) -> datetime:
        seconds = (physical_eta - observed_at).total_seconds()
        steps = max(1, ceil(seconds / 300))
        return observed_at + timedelta(minutes=5 * steps)

    @staticmethod
    def _ranking_input(feasible, prediction: PredictionResult, ports: int) -> RankingInput:
        candidate = FeasibleCandidate(
            station_id=feasible.candidate.station.station_id,
            distance_km=feasible.candidate.route.distance_km,
            detour_km=feasible.candidate.detour_km,
            arrival_soc_pct=feasible.arrival_soc_pct,
            p_available=prediction.p_available,
            eta=prediction.eta,
        )
        return RankingInput(
            candidate=candidate,
            travel_minutes=feasible.candidate.route.duration_minutes,
            working_ports=ports,
        )

    @staticmethod
    def _with_detour(feasible: FeasibleRouteCandidate, detour_km: float) -> FeasibleRouteCandidate:
        candidate = feasible.candidate
        return FeasibleRouteCandidate(
            candidate=RouteCandidate(
                station=candidate.station,
                status=candidate.status,
                route=candidate.route,
                eta=candidate.eta,
                detour_km=detour_km,
            ),
            arrival_soc_pct=feasible.arrival_soc_pct,
        )

    @staticmethod
    def _plan(candidate) -> Plan:
        return Plan(
            station_id=candidate.station_id,
            eta=candidate.eta,
            distance_km=candidate.distance_km,
            detour_km=candidate.detour_km,
            arrival_soc_pct=candidate.arrival_soc_pct,
            p_available=candidate.p_available,
        )

    def _empty_result(self, request: RecommendationRequest, reasons: list[str] | None = None):
        return RecommendationResult(
            request_id=request.request_id,
            primary=None,
            backup=None,
            plan_p=None,
            plan_p_assumption=None,
            reasons=reasons or ["No feasible charging station was found."],
            time_shift=None,
            model_version="not_used",
            allocation_method=self._allocation_method,
            data_type=self._data_type,
        )
