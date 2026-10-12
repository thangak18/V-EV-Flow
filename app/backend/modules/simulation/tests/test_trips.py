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
