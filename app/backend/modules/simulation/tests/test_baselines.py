from datetime import datetime, timedelta, timezone

from app.backend.contracts.common import Coordinate
from app.backend.contracts.enums import Scenario
from app.backend.contracts.recommendation import (
    AllocationContext,
    FeasibleCandidate,
    RecommendationRequest,
    Vehicle,
)
from app.backend.modules.simulation.baselines import CurrentlyAvailableStrategy, NearestStrategy

NOW = datetime(2026, 10, 13, 8, 0, tzinfo=timezone(timedelta(hours=7)))


def candidate(station_id: str, distance: float, soc: float = 50.0) -> FeasibleCandidate:
    return FeasibleCandidate(
        station_id=station_id,
        distance_km=distance,
        detour_km=1.0,
        arrival_soc_pct=soc,
        p_available=0.5,
        eta=NOW,
    )


def context(*candidates: FeasibleCandidate) -> AllocationContext:
    return AllocationContext(
        request=RecommendationRequest(
            request_id="r1",
            origin=Coordinate(lat=10.8, lng=106.7),
            destination=Coordinate(lat=10.4, lng=107.1),
            observed_at=NOW,
            depart_time=NOW,
            scenario=Scenario.NORMAL,
            vehicle=Vehicle(
                soc_pct=60, battery_kwh=60, consumption_kwh_per_km=0.18, connector_type="CCS2"
            ),
        ),
        candidates=candidates,
    )


def test_nearest_picks_closest_feasible_and_backup_next() -> None:
    plan = NearestStrategy().select(
        context(candidate("S3", 30), candidate("S1", 10), candidate("S2", 20))
    )
    assert plan.primary is not None and plan.primary.station_id == "S1"
    assert plan.backup is not None and plan.backup.station_id == "S2"
    assert plan.plan_p is None


def test_nearest_skips_candidates_below_soc_reserve() -> None:
    plan = NearestStrategy(min_soc_pct=10).select(
        context(candidate("S1", 5, soc=4), candidate("S2", 20))
    )
    assert plan.primary is not None and plan.primary.station_id == "S2"
    assert plan.backup is None


def test_ties_break_by_station_id() -> None:
    plan = NearestStrategy().select(context(candidate("S2", 10), candidate("S1", 10)))
    assert plan.primary is not None and plan.primary.station_id == "S1"


def test_no_feasible_station_returns_empty_plan_with_reason() -> None:
    plan = NearestStrategy().select(context(candidate("S1", 5, soc=1)))
    assert plan.primary is None and plan.backup is None
    assert plan.reasons == ["no feasible station"]
    assert NearestStrategy().select(context()).primary is None


def test_currently_available_prefers_free_station_over_nearer_full_one() -> None:
    free = {"S1": 0, "S2": 2, "S3": 1}
    strategy = CurrentlyAvailableStrategy(lambda station_id: free[station_id])
    plan = strategy.select(context(candidate("S1", 5), candidate("S3", 30), candidate("S2", 20)))
    assert plan.primary is not None and plan.primary.station_id == "S2"
    assert plan.backup is not None and plan.backup.station_id == "S3"


def test_currently_available_falls_back_to_nearest_and_says_so() -> None:
    strategy = CurrentlyAvailableStrategy(lambda _station_id: 0)
    plan = strategy.select(context(candidate("S2", 20), candidate("S1", 5)))
    assert plan.primary is not None and plan.primary.station_id == "S1"
    assert "fell back" in plan.reasons[0]
