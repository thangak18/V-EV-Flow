from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from itertools import permutations
from typing import Any, cast

import pytest
from pydantic import ValidationError

from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.errors import RouteUnavailableError
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import (
    RecommendationRequest,
    RecommendationResult,
    RouteRequest,
    RouteResult,
    StatusWindow,
    Vehicle,
)
from app.backend.contracts.stations import Station, StationStatus
from app.backend.modules.recommendation import service as service_module
from app.backend.modules.recommendation.ranking import RankingConfig
from app.backend.modules.recommendation.service import RecommendationService

VN = timezone(timedelta(hours=7))
OBSERVED = datetime(2026, 10, 14, 8, 0, tzinfo=VN)


def station(station_id: str, *, ports: int = 2) -> Station:
    return Station(
        station_id=station_id,
        name=station_id,
        lat=10.0 + ord(station_id[-1]) / 1000,
        lng=106.0 + ord(station_id[-1]) / 1000,
        n_ports=ports,
        power_kw=60,
        connector_types=["CCS2"],
        network="test",
        station_type="highway",
        source="test",
        assumptions=[],
    )


def request() -> RecommendationRequest:
    return RecommendationRequest(
        request_id="req-c5",
        origin=Coordinate(lat=10.0, lng=106.0),
        destination=Coordinate(lat=10.5, lng=106.5),
        observed_at=OBSERVED,
        depart_time=OBSERVED,
        scenario=Scenario.NORMAL,
        vehicle=Vehicle(
            soc_pct=80,
            battery_kwh=60,
            consumption_kwh_per_km=0.2,
            connector_type="CCS2",
        ),
    )


class FakeStations:
    def __init__(self, stations: tuple[Station, ...]) -> None:
        self.stations = stations

    def list_stations(self) -> tuple[Station, ...]:
        return self.stations

    def get_station(self, station_id: str) -> Station:
        return next(item for item in self.stations if item.station_id == station_id)


class FakeStatuses:
    def __init__(
        self,
        stations: FakeStations,
        *,
        broken: set[str] | None = None,
        scenario: Scenario = Scenario.NORMAL,
    ) -> None:
        self.stations = stations
        self.broken = broken or set()
        self.scenario = scenario

    def window(
        self, station_id: str, observed_at: datetime, lags: tuple[int, ...] = (15, 30, 60)
    ) -> StatusWindow:
        item = self.stations.get_station(station_id)
        broken = item.n_ports if station_id in self.broken else 0
        status = StationStatus(
            station_id=station_id,
            ts=observed_at,
            ports_free=0,
            ports_busy=item.n_ports - broken,
            ports_broken=broken,
            n_ports=item.n_ports,
            scenario=self.scenario,
        )
        return StatusWindow(
            station_id=station_id,
            observed_at=observed_at,
            lags=(0,),
            statuses=(status,),
        )


class FakeRoutes:
    def __init__(
        self,
        routes: dict[tuple[tuple[float, float], tuple[float, float]], tuple[RouteResult, ...]],
    ) -> None:
        self.routes = routes
        self.requests: list[RouteRequest] = []
        self.errors: dict[tuple[tuple[float, float], tuple[float, float]], Exception] = {}

    async def get_routes(self, request: RouteRequest) -> tuple[RouteResult, ...]:
        self.requests.append(request)
        key = (
            (request.origin.lat, request.origin.lng),
            (request.destination.lat, request.destination.lng),
        )
        if key in self.errors:
            raise self.errors[key]
        return self.routes.get(key, ())


class FakePredictor:
    def __init__(self, probabilities: dict[str, float]) -> None:
        self.probabilities = probabilities
        self.requests: list[PredictRequest] = []
        self.transform: Callable[[PredictionResult], PredictionResult] = lambda result: result

    def predict(self, request: PredictRequest) -> PredictionResult:
        self.requests.append(request)
        return self.transform(
            PredictionResult(
                station_id=request.station_id,
                eta=request.eta,
                p_available=self.probabilities[request.station_id],
                reasons=["fake prediction"],
                explanation_method="fake",
                model_version="fake-c5",
                data_type=DataType.MOCK,
            )
        )


def route(distance: float, minutes: float) -> RouteResult:
    return RouteResult(distance_km=distance, duration_minutes=minutes, source="fake")


def service(
    stations: tuple[Station, ...],
    routes: FakeRoutes,
    predictor: FakePredictor,
    *,
    broken: set[str] | None = None,
    minimum_soc: float = 10,
    travel_weight: float = 0,
    data_type: DataType = DataType.MOCK,
    max_horizon: int = 120,
) -> RecommendationService:
    repository = FakeStations(stations)
    statuses = FakeStatuses(repository, broken=broken)
    return RecommendationService(
        station_repository=repository,
        status_repositories={Scenario.NORMAL: statuses},
        route_provider=routes,
        predictors={Scenario.NORMAL: predictor},
        ranking_config=RankingConfig(
            weight_probability=1,
            weight_travel=travel_weight,
            weight_soc_risk=0,
            weight_virtual_load=0,
            min_arrival_soc_pct=minimum_soc,
        ),
        minimum_arrival_soc_pct=minimum_soc,
        data_type=data_type,
        max_prediction_horizon_minutes={Scenario.NORMAL: max_horizon},
    )


def run(service_instance: RecommendationService):
    return asyncio.run(service_instance.recommend(request()))


def test_one_feasible_station_returns_primary_only_and_preserves_prediction() -> None:
    s1 = station("S1")
    routes = FakeRoutes(
        {
            ((10.0, 106.0), (s1.lat, s1.lng)): (route(10, 11),),
            ((s1.lat, s1.lng), (10.5, 106.5)): (route(20, 20),),
            ((10.0, 106.0), (10.5, 106.5)): (route(40, 35),),
        }
    )
    predictor = FakePredictor({"S1": 0.73})

    result = run(service((s1,), routes, predictor))

    assert result.primary is not None
    assert result.primary.station_id == "S1"
    assert result.backup is None
    assert result.primary.p_available == pytest.approx(0.73)
    assert result.plan_p == pytest.approx(0.73)
    assert result.primary.eta == datetime(2026, 10, 14, 8, 15, tzinfo=VN)
    assert len(predictor.requests) == 1


def test_backup_is_reached_from_primary_without_charging_there() -> None:
    s1, s2 = station("S1"), station("S2")
    routes = FakeRoutes(
        {
            ((10.0, 106.0), (s1.lat, s1.lng)): (route(10, 10),),
            ((s1.lat, s1.lng), (s2.lat, s2.lng)): (route(15, 10),),
            ((s1.lat, s1.lng), (10.5, 106.5)): (route(20, 20),),
            ((s2.lat, s2.lng), (10.5, 106.5)): (route(10, 10),),
            ((10.0, 106.0), (10.5, 106.5)): (route(40, 35),),
        }
    )
    predictor = FakePredictor({"S1": 0.9, "S2": 0.6})

    result = run(service((s2, s1), routes, predictor))

    assert result.primary is not None and result.primary.station_id == "S1"
    assert result.backup is not None and result.backup.station_id == "S2"
    assert result.backup.distance_km == pytest.approx(25)
    assert result.backup.arrival_soc_pct == pytest.approx(71.6666666667)
    assert result.plan_p == pytest.approx(1 - (1 - 0.9) * (1 - 0.6))
    assert any(
        call.origin.lat == s1.lat and call.destination.lat == s2.lat for call in routes.requests
    )
    assert predictor.requests[-1].eta == result.backup.eta


def test_fastest_infeasible_route_does_not_hide_feasible_alternative() -> None:
    s1 = station("S1")
    routes = FakeRoutes(
        {
            ((10.0, 106.0), (s1.lat, s1.lng)): (route(400, 5), route(10, 10)),
            ((s1.lat, s1.lng), (10.5, 106.5)): (route(20, 20),),
            ((10.0, 106.0), (10.5, 106.5)): (route(40, 35),),
        }
    )
    predictor = FakePredictor({"S1": 0.7})

    result = run(service((s1,), routes, predictor))

    assert result.primary is not None
    assert result.primary.distance_km == pytest.approx(10)
    assert result.primary.eta == datetime(2026, 10, 14, 8, 10, tzinfo=VN)


def test_incompatible_or_broken_stations_never_reach_prediction() -> None:
    broken = station("S1")
    incompatible = station("S2").model_copy(update={"connector_types": ["CHAdeMO"]})
    routes = FakeRoutes(
        {
            ((10.0, 106.0), (broken.lat, broken.lng)): (route(10, 10),),
            ((10.0, 106.0), (incompatible.lat, incompatible.lng)): (route(10, 10),),
            ((10.0, 106.0), (10.5, 106.5)): (route(40, 35),),
        }
    )
    predictor = FakePredictor({"S1": 0.9, "S2": 0.9})

    result = run(service((broken, incompatible), routes, predictor, broken={"S1"}))

    assert result.primary is None
    assert predictor.requests == []


def test_empty_stations_returns_valid_no_plan() -> None:
    result = run(service((), FakeRoutes({}), FakePredictor({})))

    assert result.primary is None
    assert result.backup is None
    assert result.plan_p is None
    assert result.model_version == "not_used"


def journey(primary_minutes: float = 60) -> tuple[tuple[Station, ...], FakeRoutes, FakePredictor]:
    stations = (station("S1"), station("S2"), station("S3"))
    s1, s2, s3 = stations
    routes = FakeRoutes(
        {
            ((10.0, 106.0), (10.5, 106.5)): (route(30, 40),),
            ((10.0, 106.0), (s1.lat, s1.lng)): (route(10, primary_minutes),),
            ((s1.lat, s1.lng), (s2.lat, s2.lng)): (route(5, 5),),
            ((s1.lat, s1.lng), (s3.lat, s3.lng)): (route(10, 40),),
            **{((item.lat, item.lng), (10.5, 106.5)): (route(30, 20),) for item in stations},
        }
    )
    return stations, routes, FakePredictor({"S1": 0.99, "S2": 0.60, "S3": 0.75})


def test_backup_ranking_uses_cumulative_travel_duration() -> None:
    stations, routes, predictor = journey()
    result = run(service(stations, routes, predictor, travel_weight=0.5))
    assert result.primary is not None and result.primary.station_id == "S1"
    assert result.backup is not None and result.backup.station_id == "S3"
    assert result.backup.eta == OBSERVED + timedelta(minutes=100)
    assert result.backup.distance_km == 20
    assert result.backup.arrival_soc_pct == pytest.approx(80 - 100 * 20 * 0.2 / 60)


@pytest.mark.parametrize("primary_minutes,leg_minutes", [(0, 5), (11, 0), (11, 7)])
def test_physical_fallback_departure_and_bucket(primary_minutes: float, leg_minutes: float) -> None:
    stations, routes, predictor = journey(primary_minutes)
    s1, s2, _ = stations
    routes.routes[((s1.lat, s1.lng), (s2.lat, s2.lng))] = (route(5, leg_minutes),)
    result = run(service(stations[:2], routes, predictor))
    assert result.backup is not None
    physical = OBSERVED + timedelta(minutes=primary_minutes + leg_minutes)
    assert result.backup.eta >= physical
    assert result.backup.eta > OBSERVED
    fallback_call = next(
        call
        for call in routes.requests
        if call.origin.lat == s1.lat and call.destination.lat == s2.lat
    )
    assert fallback_call.depart_time == OBSERVED + timedelta(minutes=primary_minutes)


@pytest.mark.parametrize(
    "observed",
    [
        OBSERVED + timedelta(minutes=2),
        OBSERVED + timedelta(seconds=1),
        OBSERVED + timedelta(microseconds=1),
        OBSERVED.astimezone(UTC),
        OBSERVED.replace(tzinfo=None),
    ],
)
def test_invalid_observation_rejected_even_without_stations(observed: datetime) -> None:
    routes, predictor = FakeRoutes({}), FakePredictor({})
    invalid = request().model_copy(
        update={
            "observed_at": observed,
            "depart_time": OBSERVED + timedelta(hours=1),
        }
    )
    with pytest.raises(ValueError):
        asyncio.run(service((), routes, predictor).recommend(invalid))
    assert routes.requests == predictor.requests == []


@pytest.mark.parametrize(
    "depart",
    [OBSERVED - timedelta(minutes=1), OBSERVED.replace(tzinfo=None), OBSERVED.astimezone(UTC)],
)
def test_invalid_departure_rejected_before_routing(depart: datetime) -> None:
    routes = FakeRoutes({})
    invalid = request().model_copy(update={"depart_time": depart})
    with pytest.raises(ValueError):
        asyncio.run(service((), routes, FakePredictor({})).recommend(invalid))
    assert routes.requests == []


@pytest.mark.parametrize("kind", ["connector", "soc", "capacity", "route"])
def test_no_plan_reasons_describe_actual_rejections(kind: str) -> None:
    stations, routes, predictor = journey()
    s1 = stations[0]
    broken = None
    if kind == "connector":
        s1 = s1.model_copy(update={"connector_types": ["CHAdeMO"]})
    elif kind == "soc":
        routes.routes[((10.0, 106.0), (s1.lat, s1.lng))] = (route(500, 60),)
    elif kind == "capacity":
        broken = {"S1"}
    else:
        routes.routes.pop(((10.0, 106.0), (s1.lat, s1.lng)))
    result = run(service((s1,), routes, predictor, broken=broken))
    assert result.primary is None
    text = " ".join(result.reasons).lower()
    assert kind in text
    if kind != "route":
        assert {"connector": "incompatible", "soc": "insufficient", "capacity": "working"}[
            kind
        ] in text
    if kind == "route":
        assert "soc" not in text
    assert predictor.requests == []


def test_primary_only_reasons_do_not_imply_selected_backup() -> None:
    stations, routes, predictor = journey()
    result = run(service(stations[:1], routes, predictor))
    assert result.backup is None
    assert any("no" in reason.lower() and "backup" in reason.lower() for reason in result.reasons)
    assert not any("backup route starts" in reason.lower() for reason in result.reasons)


def test_empty_dataset_reason_is_explicit() -> None:
    result = run(service((), FakeRoutes({}), FakePredictor({})))
    assert any("dataset" in reason.lower() for reason in result.reasons)


@pytest.mark.parametrize("source", [DataType.MOCK, DataType.SIMULATED])
def test_no_plan_provenance_is_explicit_and_model_unused(source: DataType) -> None:
    result = run(service((), FakeRoutes({}), FakePredictor({}), data_type=source))
    assert result.data_type == source
    assert result.model_version == "not_used"
    assert result.allocation_method == "heuristic_ranking"


@pytest.mark.parametrize(
    "field,value",
    [
        ("station_id", "wrong"),
        ("eta", OBSERVED),
        ("p_available", float("nan")),
        ("p_available", 1.1),
        ("model_version", ""),
        ("contract_version", "99.0"),
        ("data_type", "invalid"),
    ],
)
def test_predictor_corrupt_or_mismatched_response_rejected(field: str, value: object) -> None:
    stations, routes, predictor = journey()
    predictor.transform = lambda result: result.model_copy(update={field: value})
    with pytest.raises(ValueError):
        run(service(stations[:1], routes, predictor))


@pytest.mark.parametrize(
    "field,value", [("model_version", "other"), ("data_type", DataType.SIMULATED)]
)
def test_incompatible_primary_backup_prediction_evidence_rejected(
    field: str, value: object
) -> None:
    stations, routes, predictor = journey()
    predictor.transform = lambda result: (
        result.model_copy(update={field: value}) if result.station_id == "S2" else result
    )
    with pytest.raises(ValueError):
        run(service(stations[:2], routes, predictor))


@pytest.mark.parametrize("problem", ["authentication", "rate_limit", "connection", "malformed"])
def test_ambiguous_provider_errors_propagate(problem: str) -> None:
    stations, routes, predictor = journey()
    s1 = stations[0]
    failure = RouteUnavailableError(problem)
    routes.errors[((10.0, 106.0), (s1.lat, s1.lng))] = failure
    with pytest.raises(RouteUnavailableError) as raised:
        run(service(stations, routes, predictor))
    assert raised.value is failure


def test_missing_origin_station_route_preserves_valid_primary() -> None:
    stations, routes, predictor = journey()
    result = run(service(stations, routes, predictor))
    assert result.primary is not None and result.primary.station_id == "S1"


def test_unavailable_backup_edge_preserves_other_backup() -> None:
    stations, routes, predictor = journey()
    s1, s2, _ = stations
    routes.routes.pop(((s1.lat, s1.lng), (s2.lat, s2.lng)))
    result = run(service(stations, routes, predictor))
    assert result.backup is not None and result.backup.station_id == "S3"


def test_recommendation_is_deterministic_and_contract_valid() -> None:
    results = []
    stations, _, _ = journey()
    for ordered in permutations(stations):
        _, routes, predictor = journey()
        result = run(service(ordered, routes, predictor))
        results.append(RecommendationResult.model_validate_json(result.model_dump_json()))
    assert all(result == results[0] for result in results)


def test_unsupported_model_horizon_is_not_hidden() -> None:
    stations, routes, predictor = journey(65)

    def enforce_horizon(result: PredictionResult) -> PredictionResult:
        if result.eta - OBSERVED > timedelta(minutes=60):
            raise ValueError("unsupported prediction horizon")
        return result

    predictor.transform = enforce_horizon
    with pytest.raises(ValueError, match="horizon"):
        run(service(stations, routes, predictor))


def test_naive_request_rejected_by_shared_contract() -> None:
    payload = request().model_dump()
    payload["observed_at"] = OBSERVED.replace(tzinfo=None)
    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate(payload)


def test_provenance_must_be_explicit_at_composition() -> None:
    repository = FakeStations(())
    dependencies: dict[str, Any] = dict(
        station_repository=repository,
        status_repositories={Scenario.NORMAL: FakeStatuses(repository)},
        route_provider=FakeRoutes({}),
        predictors={Scenario.NORMAL: FakePredictor({})},
        ranking_config=RankingConfig(),
    )
    with pytest.raises(TypeError):
        RecommendationService(**dependencies)


def test_no_plan_never_claims_model_was_used() -> None:
    predictor = FakePredictor({})
    assert run(service((), FakeRoutes({}), predictor)).model_version == "not_used"
    assert predictor.requests == []


@pytest.mark.parametrize("primary_minutes,expected", [(0, "S2"), (60, "S3")])
def test_primary_duration_changes_actual_backup_travel_penalty(
    primary_minutes: float,
    expected: str,
) -> None:
    stations, routes, predictor = journey(primary_minutes)
    result = run(service(stations, routes, predictor, travel_weight=0.5))
    assert result.backup is not None and result.backup.station_id == expected


def test_cumulative_route_metadata_does_not_claim_leg_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stations, routes, predictor = journey(11)
    s1, s2, _ = stations
    routes.routes[((s1.lat, s1.lng), (s2.lat, s2.lng))] = (
        route(5, 7).model_copy(update={"geometry": (Coordinate(lat=s1.lat, lng=s1.lng),)}),
    )
    original = service_module.evaluate_feasibility
    cumulative = []

    def inspect(vehicle, candidates, minimum):
        cumulative.extend(
            item.route for item in candidates if item.route.source.startswith("cumulative:")
        )
        return original(vehicle, candidates, minimum)

    monkeypatch.setattr(service_module, "evaluate_feasibility", inspect)
    result = run(service(stations[:2], routes, predictor))
    assert result.backup is not None
    assert len(cumulative) == 1
    assert cumulative[0].distance_km == 15
    assert cumulative[0].duration_minutes == 18
    assert cumulative[0].geometry is None


@pytest.mark.parametrize("reason", ["soc", "route"])
def test_backup_failure_retains_primary_with_correct_reasons(reason: str) -> None:
    stations, routes, predictor = journey(11)
    s1, s2, _ = stations
    edge = ((s1.lat, s1.lng), (s2.lat, s2.lng))
    routes.routes[edge] = () if reason == "route" else (route(500, 5),)
    result = run(service(stations[:2], routes, predictor))
    assert result.primary is not None and result.backup is None
    assert result.plan_p == result.primary.p_available
    assert result.plan_p_assumption is None
    text = " ".join(result.reasons).lower()
    assert "no reachable/eligible backup" in text
    assert reason in text


def test_fallback_prediction_is_fresh_and_probability_is_preserved() -> None:
    stations, routes, predictor = journey(11)
    s1, s2, _ = stations
    routes.routes[((10.0, 106.0), (s2.lat, s2.lng))] = (route(5, 5),)
    predictor.transform = lambda result: (
        result.model_copy(
            update={
                "p_available": 0.60 if result.eta >= OBSERVED + timedelta(minutes=15) else 0.50,
            }
        )
        if result.station_id == "S2"
        else result
    )
    result = run(service(stations[:2], routes, predictor))
    assert result.primary is not None and result.backup is not None
    assert result.backup.p_available == 0.60
    assert result.primary.p_available == 0.99
    assert result.plan_p == pytest.approx(1 - (1 - 0.99) * (1 - 0.60))
    assert result.model_version == "fake-c5" and result.data_type == DataType.MOCK
    assert result.plan_p_assumption == "independent_stations"
    assert any("independent" in reason for reason in result.reasons)
    assert {item.eta for item in predictor.requests if item.station_id == "S2"} == {
        OBSERVED + timedelta(minutes=5),
        OBSERVED + timedelta(minutes=20),
    }


def test_source_and_model_provenance_are_combined_explicitly() -> None:
    stations, routes, predictor = journey()
    result = run(service(stations[:1], routes, predictor, data_type=DataType.SIMULATED))
    assert result.data_type == DataType.MIXED
    assert result.model_version == "fake-c5"


@pytest.mark.parametrize("scenario", list(Scenario))
def test_scenario_dependencies_are_selected_without_cross_contamination(scenario: Scenario) -> None:
    stations, routes, _ = journey(11)
    repository = FakeStations(stations[:1])
    predictors = {key: FakePredictor({"S1": 0.9}) for key in Scenario}
    instance = RecommendationService(
        station_repository=repository,
        status_repositories={key: FakeStatuses(repository, scenario=key) for key in Scenario},
        route_provider=routes,
        predictors=predictors,
        ranking_config=RankingConfig(),
        data_type=DataType.MOCK,
        max_prediction_horizon_minutes={key: 120 for key in Scenario},
    )
    result = asyncio.run(instance.recommend(request().model_copy(update={"scenario": scenario})))
    assert result.primary is not None
    assert predictors[scenario].requests[0].scenario == scenario
    assert all(not predictor.requests for key, predictor in predictors.items() if key != scenario)


def test_missing_scenario_dependency_is_not_defaulted_to_normal() -> None:
    invalid = request().model_copy(update={"scenario": Scenario.TET})
    with pytest.raises(ValueError, match="scenario"):
        asyncio.run(service((), FakeRoutes({}), FakePredictor({})).recommend(invalid))


@pytest.mark.parametrize(
    "field,value",
    [
        ("station_id", "wrong"),
        ("scenario", Scenario.TET),
        ("ts", OBSERVED + timedelta(minutes=5)),
        ("n_ports", 3),
    ],
)
def test_status_window_corruption_is_rejected(field: str, value: object) -> None:
    stations, routes, predictor = journey()
    repository = FakeStations(stations[:1])

    class CorruptStatuses(FakeStatuses):
        def window(self, station_id, observed_at, lags=(15, 30, 60)):
            result = super().window(station_id, observed_at, lags)
            return result.model_copy(
                update={
                    "statuses": (result.statuses[0].model_copy(update={field: value}),),
                }
            )

    instance = RecommendationService(
        station_repository=repository,
        status_repositories={Scenario.NORMAL: CorruptStatuses(repository)},
        route_provider=routes,
        predictors={Scenario.NORMAL: predictor},
        ranking_config=RankingConfig(),
        data_type=DataType.MOCK,
        max_prediction_horizon_minutes={Scenario.NORMAL: 120},
    )
    with pytest.raises(ValueError):
        run(instance)
    assert predictor.requests == []


@pytest.mark.parametrize("minutes", [0, 11, 60])
def test_backup_duration_passed_to_c4_is_cumulative(
    minutes: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stations, routes, predictor = journey(minutes)
    original = service_module.rank_candidates
    inputs = []

    def inspect(candidates, config, loads):
        inputs.append(tuple(candidates))
        return original(candidates, config, loads)

    monkeypatch.setattr(service_module, "rank_candidates", inspect)
    run(service(stations, routes, predictor))
    assert {item.candidate.station_id: item.travel_minutes for item in inputs[1]} == {
        "S2": minutes + 5,
        "S3": minutes + 40,
    }


def limited_predictor() -> FakePredictor:
    predictor = FakePredictor({"S1": 0.9, "S2": 0.8, "S3": 0.7})

    def enforce(result: PredictionResult) -> PredictionResult:
        if result.eta - OBSERVED > timedelta(minutes=60):
            raise ValueError("model horizon exceeded")
        return result

    predictor.transform = enforce
    return predictor


def test_supported_primary_survives_unrelated_unsupported_origin_candidate() -> None:
    stations, routes, _ = journey(10)
    s2 = stations[1]
    routes.routes[((10.0, 106.0), (s2.lat, s2.lng))] = (route(20, 90),)
    predictor = limited_predictor()
    result = run(service(stations, routes, predictor, max_horizon=60))
    assert result.primary is not None and result.primary.station_id == "S1"
    assert all(item.eta - OBSERVED <= timedelta(minutes=60) for item in predictor.requests)


def test_supported_primary_survives_unsupported_cumulative_backup() -> None:
    stations, routes, _ = journey(55)
    predictor = limited_predictor()
    result = run(service(stations, routes, predictor, max_horizon=60))
    assert result.primary is not None and result.backup is not None
    assert result.backup.station_id == "S2"
    assert all(item.station_id != "S3" for item in predictor.requests)


def test_all_out_of_horizon_returns_no_plan_without_inference() -> None:
    stations, routes, _ = journey(90)
    predictor = limited_predictor()
    result = run(service(stations[:1], routes, predictor, max_horizon=60))
    assert result.primary is None
    assert predictor.requests == []
    assert "horizon" in " ".join(result.reasons)


@pytest.mark.parametrize("minutes,has_primary", [(57, True), (58, False)])
def test_horizon_uses_departure_offset_and_ceiling_bucket(
    minutes: float, has_primary: bool
) -> None:
    stations, routes, _ = journey(minutes)
    predictor = limited_predictor()
    instance = service(stations[:1], routes, predictor, max_horizon=60)
    late_departure = request().model_copy(update={"depart_time": OBSERVED + timedelta(minutes=3)})
    result = asyncio.run(instance.recommend(late_departure))
    assert (result.primary is not None) == has_primary
    if result.primary is not None:
        assert result.primary.eta == OBSERVED + timedelta(minutes=60)
    else:
        assert predictor.requests == []
        assert "horizon" in " ".join(result.reasons)


def test_primary_only_reports_unsupported_backup_without_inference() -> None:
    stations, routes, _ = journey(55)
    s1, s2, _ = stations
    routes.routes[((s1.lat, s1.lng), (s2.lat, s2.lng))] = (route(5, 10),)
    predictor = limited_predictor()
    result = run(service(stations[:2], routes, predictor, max_horizon=60))
    assert result.primary is not None and result.backup is None
    assert result.plan_p == result.primary.p_available
    assert [item.station_id for item in predictor.requests] == ["S1"]
    assert "horizon" in " ".join(result.reasons)


@pytest.mark.parametrize("maximum", [0, -1, True, 60.5, float("inf"), "60", None])
def test_invalid_horizon_configuration_fails_explicitly(maximum: object) -> None:
    with pytest.raises(ValueError, match="horizon"):
        service((), FakeRoutes({}), FakePredictor({}), max_horizon=cast(int, maximum))


def test_missing_horizon_configuration_fails_at_composition() -> None:
    repository = FakeStations(())
    dependencies: dict[str, Any] = dict(
        station_repository=repository,
        status_repositories={Scenario.NORMAL: FakeStatuses(repository)},
        route_provider=FakeRoutes({}),
        predictors={Scenario.NORMAL: FakePredictor({})},
        ranking_config=RankingConfig(),
        data_type=DataType.MOCK,
    )
    with pytest.raises(TypeError):
        RecommendationService(**dependencies)
    dependencies["max_prediction_horizon_minutes"] = {}
    with pytest.raises(ValueError, match="scenarios"):
        RecommendationService(**dependencies)


@pytest.mark.parametrize("scenario,has_primary", [(Scenario.NORMAL, True), (Scenario.TET, False)])
def test_horizon_capabilities_are_scenario_specific(scenario: Scenario, has_primary: bool) -> None:
    stations, routes, _ = journey(11)
    repository = FakeStations(stations[:1])
    predictors = {key: limited_predictor() for key in (Scenario.NORMAL, Scenario.TET)}
    instance = RecommendationService(
        station_repository=repository,
        status_repositories={key: FakeStatuses(repository, scenario=key) for key in predictors},
        route_provider=routes,
        predictors=predictors,
        ranking_config=RankingConfig(),
        data_type=DataType.MOCK,
        max_prediction_horizon_minutes={Scenario.NORMAL: 60, Scenario.TET: 10},
    )
    result = asyncio.run(instance.recommend(request().model_copy(update={"scenario": scenario})))
    assert (result.primary is not None) == has_primary
    assert not predictors[Scenario.TET].requests


def test_supported_horizon_does_not_swallow_unexpected_inference_failure() -> None:
    stations, routes, predictor = journey(10)

    def fail(_: PredictionResult) -> PredictionResult:
        raise ValueError("corrupt inference features")

    predictor.transform = fail
    with pytest.raises(ValueError, match="corrupt inference features"):
        run(service(stations, routes, predictor, max_horizon=60))
