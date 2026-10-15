from datetime import timedelta

from app.backend.modules.simulation.tests.test_runner import make_bundle, make_config, make_vehicles
from app.backend.modules.simulation.trips import build_trips


def test_trips_are_deterministic_ordered_and_inside_the_departure_window() -> None:
    bundle, config = make_bundle(make_vehicles(50)), make_config()
    first, second = build_trips(bundle, config, 50), build_trips(bundle, config, 50)
    assert first == second
    assert [t.depart_at for t in first] == sorted(t.depart_at for t in first)
    assert len({t.vehicle_id for t in first}) == 50
    assert all(config.end - timedelta(hours=24) < t.depart_at <= config.end for t in first)
    assert all(t.depart_at <= config.end - timedelta(hours=4) for t in first)


def test_different_seed_changes_trips_and_compliance_rate_is_respected() -> None:
    config = make_config()
    base = build_trips(make_bundle(make_vehicles(50), seed=5), config, 50)
    other = build_trips(make_bundle(make_vehicles(50), seed=6), config, 50)
    assert base != other
    assert all(t.complies for t in build_trips(make_bundle(make_vehicles(5)), make_config(1.0), 5))
    assert not any(
        t.complies for t in build_trips(make_bundle(make_vehicles(5)), make_config(0.0), 5)
    )


def test_departures_spread_over_twenty_hours_and_leave_four_hours_to_arrive() -> None:
    bundle, config = make_bundle(make_vehicles(200)), make_config()
    departures = [t.depart_at for t in build_trips(bundle, config, 200)]
    first_allowed = config.end - timedelta(hours=24) + timedelta(minutes=config.step_minutes)
    last_allowed = config.end - timedelta(hours=4)
    assert min(departures) >= first_allowed
    assert max(departures) <= last_allowed
    assert max(departures) - min(departures) >= timedelta(hours=18)
    assert len({d.hour for d in departures}) >= 15


def test_shifted_population_is_exact_reproducible_and_only_changes_departures() -> None:
    from datetime import datetime, timedelta

    from app.backend.contracts.common import Coordinate
    from app.backend.contracts.enums import Scenario
    from app.backend.contracts.recommendation import Vehicle
    from app.backend.contracts.simulation import ScenarioConfig
    from app.backend.modules.simulation.trips import VehicleTrip, shift_to_offpeak

    start = datetime.fromisoformat("2026-10-13T00:00:00+07:00")
    config = ScenarioConfig(
        scenario=Scenario.NORMAL,
        seed=42,
        start=start,
        end=start + timedelta(hours=23, minutes=55),
        step_minutes=5,
        demand_multiplier=1,
        compliance_rate=1,
    )
    vehicle = Vehicle(
        soc_pct=30, battery_kwh=60, consumption_kwh_per_km=0.18, connector_type="CCS2"
    )
    origin = Coordinate(lat=10.78, lng=106.7)
    trips = tuple(
        VehicleTrip(str(i), vehicle, origin, origin, start + timedelta(minutes=i * 5), True)
        for i in range(100)
    )
    shifted, count = shift_to_offpeak(trips, config, 0.2, 21)
    assert count == 20
    assert shift_to_offpeak(trips, config, 0.58, 21)[1] == 58
    original = {trip.vehicle_id: trip for trip in trips}
    assert sum(trip.depart_at != original[trip.vehicle_id].depart_at for trip in shifted) == 20
    assert {trip.vehicle_id for trip in shifted} == set(original)
    assert all(trip.vehicle == original[trip.vehicle_id].vehicle for trip in shifted)
    assert shift_to_offpeak(trips, config, 0.2, 21) == (shifted, count)
    assert all(
        trip.depart_at.hour == 21
        for trip in shifted
        if trip.depart_at != original[trip.vehicle_id].depart_at
    )
