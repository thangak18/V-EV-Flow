"""Pure pre-prediction feasibility behavior; all inputs are synthetic."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.backend.contracts.enums import Scenario
from app.backend.contracts.recommendation import FeasibleCandidate, RouteResult, Vehicle
from app.backend.contracts.stations import Station, StationStatus
from app.backend.modules.recommendation import soc


def vehicle(**overrides: object) -> Vehicle:
    values = dict(soc_pct=20, battery_kwh=60, consumption_kwh_per_km=0.18, connector_type="CCS2")
    return Vehicle.model_validate(values | overrides)


def candidate(
    station_id: str = "S001",
    *,
    connectors: tuple[str, ...] = ("CCS2",),
    free: int = 1,
    busy: int = 1,
    broken: int = 0,
    distance: float = 15,
) -> soc.RouteCandidate:
    station = Station(
        station_id=station_id,
        name=station_id,
        lat=10.7,
        lng=106.7,
        n_ports=2,
        power_kw=60,
        connector_types=list(connectors),
        network="synthetic",
        station_type="urban",
        source="synthetic-test",
        assumptions=["test only"],
    )
    status = StationStatus(
        station_id=station_id,
        ts=datetime(2026, 10, 13, 0, tzinfo=UTC),
        n_ports=2,
        ports_free=free,
        ports_busy=busy,
        ports_broken=broken,
        scenario=Scenario.NORMAL,
    )
    return soc.RouteCandidate(
        station=station,
        status=status,
        route=RouteResult(distance_km=distance, duration_minutes=30, source="synthetic"),
        eta=datetime(2026, 10, 13, 0, 30, tzinfo=UTC),
        detour_km=2,
    )


@pytest.mark.parametrize("distance, expected", [(15, 15.5), (0, 20), (100, -10)])
def test_arrival_soc_formula_and_no_mutation(distance: float, expected: float) -> None:
    car = vehicle()
    before = car.model_dump()
    assert soc.arrival_soc_pct(car, distance) == pytest.approx(expected)
    assert car.model_dump() == before


@pytest.mark.parametrize("distance", [-1, float("nan"), float("inf"), -float("inf")])
def test_arrival_soc_rejects_invalid_distance(distance: float) -> None:
    with pytest.raises(ValueError, match="distance_km"):
        soc.arrival_soc_pct(vehicle(), distance)


@pytest.mark.parametrize("field", ["battery_kwh", "consumption_kwh_per_km"])
@pytest.mark.parametrize("value", [0, -1, float("nan"), -float("inf")])
def test_vehicle_contract_rejects_invalid_positive_fields(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        vehicle(**{field: value})


@pytest.mark.parametrize("field", ["battery_kwh", "consumption_kwh_per_km"])
def test_arrival_soc_rejects_infinity_allowed_by_vehicle_contract(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        soc.arrival_soc_pct(vehicle(**{field: float("inf")}), 15)


def test_arrival_soc_rejects_arithmetic_overflow() -> None:
    with pytest.raises(ValueError, match="finite"):
        soc.arrival_soc_pct(vehicle(consumption_kwh_per_km=1e308), 1e308)


def test_arrival_soc_does_not_round() -> None:
    assert soc.arrival_soc_pct(vehicle(), 0.001) == pytest.approx(19.9997, abs=1e-12)


@pytest.mark.parametrize(
    "connectors, compatible",
    [
        (("CCS2",), True),
        (("CHAdeMO",), False),
        (("ccs2",), False),
        (("CCS2 ",), False),
        (("CCS2", "CHAdeMO"), True),
    ],
)
def test_connector_compatibility_is_exact(connectors: tuple[str, ...], compatible: bool) -> None:
    assert (
        soc.connector_compatible(vehicle(), candidate(connectors=connectors).station) is compatible
    )


@pytest.mark.parametrize("free,busy,broken,expected", [(0, 2, 0, 2), (1, 0, 1, 1), (0, 0, 2, 0)])
def test_working_ports_include_busy_ports(free: int, busy: int, broken: int, expected: int) -> None:
    item = candidate(free=free, busy=busy, broken=broken)
    assert soc.working_ports(item.station, item.status) == expected


@pytest.mark.parametrize("mismatch", ["station_id", "n_ports"])
def test_station_status_mismatch_is_input_error(mismatch: str) -> None:
    item = candidate()
    values = item.status.model_dump()
    if mismatch == "station_id":
        values["station_id"] = "OTHER"
    else:
        values.update(n_ports=3, ports_free=2)
    status = StationStatus.model_validate(values)
    with pytest.raises(ValueError, match=mismatch):
        soc.working_ports(item.station, status)
    with pytest.raises(ValueError, match=mismatch):
        soc.filter_feasible(vehicle(), [replace(item, status=status)], 10)


def test_port_invariants_are_enforced_by_contract() -> None:
    values = candidate().status.model_dump()
    for updates in ({"ports_free": -1}, {"ports_free": 2}):
        with pytest.raises(ValidationError):
            StationStatus.model_validate(values | updates)


@pytest.mark.parametrize(
    "distance,accepted", [(100 / 3, True), (100 / 3 + 0.001, False), (100, False)]
)
def test_filter_soc_threshold_and_negative_soc(distance: float, accepted: bool) -> None:
    assert bool(soc.filter_feasible(vehicle(), [candidate(distance=distance)], 10)) is accepted


@pytest.mark.parametrize("threshold", [-1, 101, float("nan"), float("inf"), -float("inf")])
def test_threshold_validated_even_for_empty_input(threshold: float) -> None:
    with pytest.raises(ValueError, match="min_soc_pct"):
        soc.filter_feasible(vehicle(), [], threshold)


@pytest.mark.parametrize("threshold", [0, 100])
def test_threshold_endpoints(threshold: float) -> None:
    assert soc.filter_feasible(vehicle(soc_pct=threshold), [candidate(distance=0)], threshold)


def test_empty_candidates() -> None:
    assert soc.filter_feasible(vehicle(), [], 10) == ()
    result = soc.evaluate_feasibility(vehicle(), [], 10)
    assert result.accepted == result.rejected == ()


def test_structured_reasons_and_deterministic_first_failure() -> None:
    items = [
        candidate("wrong", connectors=("CHAdeMO",), broken=2, free=0, busy=0, distance=100),
        candidate("mixed", connectors=("CCS2", "CHAdeMO")),
        candidate("broken", broken=2, free=0, busy=0),
        candidate("low-soc", distance=100),
        candidate("busy", free=0, busy=2),
    ]
    result = soc.evaluate_feasibility(vehicle(), items, 10)
    assert [item.candidate.station.station_id for item in result.rejected] == [
        "wrong",
        "mixed",
        "broken",
        "low-soc",
    ]
    assert [item.reason.value for item in result.rejected] == [
        "connector_incompatible",
        "connector_capacity_unknown",
        "no_working_ports",
        "insufficient_arrival_soc",
    ]
    assert [item.candidate.station.station_id for item in result.accepted] == ["busy"]
    assert result == soc.evaluate_feasibility(vehicle(), items, 10)


def test_mixed_connector_aggregate_status_never_proves_capacity() -> None:
    for counts in [(2, 0, 0), (0, 2, 0), (0, 0, 2)]:
        item = candidate(
            connectors=("CCS2", "CHAdeMO"), free=counts[0], busy=counts[1], broken=counts[2]
        )
        result = soc.evaluate_feasibility(vehicle(), [item], 10)
        assert not result.accepted
        assert result.rejected[0].reason.value == "connector_capacity_unknown"


@pytest.mark.parametrize("distance", [float("inf")])
def test_invalid_route_is_error_even_if_connector_incompatible(distance: float) -> None:
    with pytest.raises(ValueError, match="distance_km"):
        soc.filter_feasible(vehicle(), [candidate(connectors=("CHAdeMO",), distance=distance)], 10)


@pytest.mark.parametrize(
    "field,value",
    [
        ("detour_km", -1),
        ("detour_km", float("nan")),
        ("detour_km", float("inf")),
        ("eta", datetime(2026, 10, 13)),
    ],
)
def test_invalid_internal_candidate(field: str, value: object) -> None:
    item = candidate()
    with pytest.raises(ValueError, match=field):
        soc.filter_feasible(vehicle(), [replace(item, **{field: value})], 10)


def test_missing_status_is_not_feasible() -> None:
    with pytest.raises(ValueError, match="status"):
        soc.filter_feasible(vehicle(), [replace(candidate(), status=None)], 10)


def test_filter_preserves_input_order_route_and_no_mutation() -> None:
    items = [candidate("S003"), candidate("S001"), candidate("S002")]
    before = [
        (item.station.model_dump(), item.status.model_dump(), item.route.model_dump())
        for item in items
    ]
    car = vehicle()
    result = soc.filter_feasible(car, iter(items), 10)
    assert isinstance(result, tuple)
    assert [item.candidate for item in result] == items
    assert all(item.arrival_soc_pct == pytest.approx(15.5) for item in result)
    assert not hasattr(result[0], "p_available")
    assert before == [
        (item.station.model_dump(), item.status.model_dump(), item.route.model_dump())
        for item in items
    ]
    assert car == vehicle()
    with pytest.raises(FrozenInstanceError):
        setattr(result[0], "arrival_soc_pct", 0)


def test_c5_can_combine_feasibility_with_real_prediction_value() -> None:
    accepted = soc.filter_feasible(vehicle(), [candidate()], 10)[0]
    selected = accepted.candidate
    predicted_probability = 0.63
    canonical = FeasibleCandidate(
        station_id=selected.station.station_id,
        distance_km=selected.route.distance_km,
        detour_km=selected.detour_km,
        eta=selected.eta,
        arrival_soc_pct=accepted.arrival_soc_pct,
        p_available=predicted_probability,
    )
    assert canonical.p_available == predicted_probability


def test_public_package_exports() -> None:
    from app.backend.modules import recommendation

    for name in (
        "arrival_soc_pct",
        "connector_compatible",
        "working_ports",
        "filter_feasible",
        "evaluate_feasibility",
        "RouteCandidate",
        "FeasibleRouteCandidate",
        "RejectionReason",
        "RejectedCandidate",
        "FeasibilityResult",
    ):
        assert getattr(recommendation, name) is getattr(soc, name)
