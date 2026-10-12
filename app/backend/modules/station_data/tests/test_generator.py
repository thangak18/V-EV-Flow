import json
from collections import Counter
from datetime import timedelta
from pathlib import Path

import pytest

from app.backend.contracts.enums import DataType, Scenario
from app.backend.modules.station_data.generator import generate_fixture_bundle, step_times
from app.backend.modules.station_data.loaders import (
    SCENARIOS_PATH,
    STATIONS_PATH,
    load_scenario_specs,
    load_stations,
)
from app.backend.modules.station_data.manifests import (
    BUNDLE_FILE,
    MANIFEST_FILE,
    build_manifest,
    fixture_hash,
    load_fixture_bundle,
    write_fixture_bundle,
)


@pytest.fixture(scope="module")
def stations():  # noqa: ANN201
    return load_stations(STATIONS_PATH)


@pytest.fixture(scope="module")
def spec():  # noqa: ANN201
    return load_scenario_specs(SCENARIOS_PATH)[Scenario.NORMAL]


def test_same_seed_produces_identical_fixture_bundle(spec, stations) -> None:  # noqa: ANN001
    first = generate_fixture_bundle(spec, stations, vehicle_count=100)
    second = generate_fixture_bundle(spec, stations, vehicle_count=100)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert fixture_hash(first) == fixture_hash(second)


def test_different_seed_changes_bundle(spec, stations) -> None:  # noqa: ANN001
    other = spec.model_copy(update={"seed": 7})
    first = generate_fixture_bundle(spec, stations, vehicle_count=100)
    second = generate_fixture_bundle(other, stations, vehicle_count=100)
    assert fixture_hash(first) != fixture_hash(second)


def test_bundle_counts_and_bounds(spec, stations) -> None:  # noqa: ANN001
    bundle = generate_fixture_bundle(spec, stations, vehicle_count=100)
    ids = {station.station_id for station in stations}
    times = step_times(spec.to_config())
    low, high = spec.charging_minutes
    assert len(times) == 288
    assert len(bundle.vehicles) == 100
    assert bundle.background_arrivals
    assert len(bundle.service_durations) == len(bundle.background_arrivals)
    assert all(low <= item <= high for item in bundle.service_durations)
    assert all(item.station_id in ids for item in bundle.background_arrivals)
    assert all(times[0] <= item.ts <= times[-1] for item in bundle.background_arrivals)
    assert len({item.vehicle_id for item in bundle.background_arrivals}) == len(
        bundle.background_arrivals
    )
    assert all(0 <= item.soc_pct <= 100 for item in bundle.vehicles)


def test_zero_vehicles_is_valid(spec, stations) -> None:  # noqa: ANN001
    assert generate_fixture_bundle(spec, stations, vehicle_count=0).vehicles == ()


def test_invalid_inputs_are_rejected(spec, stations) -> None:  # noqa: ANN001
    with pytest.raises(ValueError, match="non-negative"):
        generate_fixture_bundle(spec, stations, vehicle_count=-1)
    with pytest.raises(ValueError, match="station"):
        generate_fixture_bundle(spec, (), vehicle_count=1)


def test_port_events_never_exceed_station_capacity(spec, stations) -> None:  # noqa: ANN001
    bundle = generate_fixture_bundle(spec, stations, vehicle_count=0)
    capacity = {station.station_id: station.n_ports for station in stations}
    broken: Counter[str] = Counter()
    assert bundle.port_events
    for event in bundle.port_events:  # events are stored in time order
        broken[event.station_id] -= event.ports_delta
        assert 0 <= broken[event.station_id] <= capacity[event.station_id]


def test_holiday_scenarios_have_more_arrivals(stations) -> None:  # noqa: ANN001
    specs = load_scenario_specs(SCENARIOS_PATH)
    counts = {
        name: len(generate_fixture_bundle(item, stations, 0).background_arrivals)
        for name, item in specs.items()
    }
    assert counts[Scenario.TET] > counts[Scenario.NORMAL]


def test_manifest_is_labelled_simulated_and_hash_stable(spec, stations, tmp_path: Path) -> None:  # noqa: ANN001
    bundle = generate_fixture_bundle(spec, stations, vehicle_count=100)
    manifest = write_fixture_bundle(bundle, tmp_path)
    assert manifest.data_type is DataType.SIMULATED
    assert manifest.fixture_hash == build_manifest(bundle).fixture_hash
    assert manifest.counts["vehicles"] == 100
    assert manifest.generated_at.utcoffset() == timedelta(hours=7)
    on_disk = json.loads((tmp_path / MANIFEST_FILE).read_text())
    assert on_disk["fixture_hash"] == manifest.fixture_hash
    assert load_fixture_bundle(tmp_path / BUNDLE_FILE) == bundle


def test_tampered_bundle_fails_hash_check(spec, stations, tmp_path: Path) -> None:  # noqa: ANN001
    bundle = generate_fixture_bundle(spec, stations, vehicle_count=3)
    write_fixture_bundle(bundle, tmp_path)
    path = tmp_path / BUNDLE_FILE
    payload = json.loads(path.read_text())
    payload["seed"] = 999
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_fixture_bundle(path)
