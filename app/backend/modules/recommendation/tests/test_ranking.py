"""Deterministic ranking tests using synthetic predictions and route metadata."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace
from datetime import UTC, datetime
from itertools import permutations
from math import isfinite
from types import MappingProxyType
from typing import Any, cast

import pytest

from app.backend.contracts.recommendation import FeasibleCandidate, RankedCandidate
from app.backend.modules.recommendation import ranking


def config(**overrides: object) -> ranking.RankingConfig:
    values: dict[str, Any] = dict(
        weight_probability=1.0,
        weight_travel=0.0,
        weight_soc_risk=0.0,
        weight_virtual_load=0.0,
        travel_reference_minutes=30.0,
        min_arrival_soc_pct=10.0,
        soc_risk_band_pct=20.0,
    )
    values.update(overrides)
    return ranking.RankingConfig(**values)


def item(
    station_id: str = "S001",
    *,
    probability: float = 0.8,
    arrival_soc: float = 30,
    travel: float = 30,
    ports: int = 2,
    distance: float = 15,
) -> ranking.RankingInput:
    return ranking.RankingInput(
        candidate=FeasibleCandidate(
            station_id=station_id,
            distance_km=distance,
            detour_km=2,
            arrival_soc_pct=arrival_soc,
            p_available=probability,
            eta=datetime(2026, 10, 13, 10, tzinfo=UTC),
        ),
        travel_minutes=travel,
        working_ports=ports,
    )


@pytest.mark.parametrize(
    "field",
    [
        "weight_probability",
        "weight_travel",
        "weight_soc_risk",
        "weight_virtual_load",
        "travel_reference_minutes",
        "min_arrival_soc_pct",
        "soc_risk_band_pct",
    ],
)
@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), -float("inf"), True, "1", None])
def test_config_rejects_invalid_numbers(field: str, value: object) -> None:
    with pytest.raises(ValueError, match=field):
        config(**{field: value})


@pytest.mark.parametrize("field", ["travel_reference_minutes", "soc_risk_band_pct"])
def test_config_denominators_must_be_positive(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        config(**{field: 0})


def test_config_rejects_all_zero_weights_and_invalid_threshold() -> None:
    with pytest.raises(ValueError, match="weight"):
        config(weight_probability=0)
    with pytest.raises(ValueError, match="min_arrival_soc_pct"):
        config(min_arrival_soc_pct=101)


def test_config_preserves_unsummed_weights_and_is_frozen() -> None:
    chosen = config(weight_probability=2, weight_travel=3)
    assert chosen.weight_probability == 2
    assert chosen.weight_travel == 3
    with pytest.raises(FrozenInstanceError):
        setattr(chosen, "weight_probability", 0)


@pytest.mark.parametrize(
    "field,value",
    [
        ("weight_probability", True),
        ("weight_travel", -1),
        ("travel_reference_minutes", 0),
        ("soc_risk_band_pct", 0),
    ],
)
def test_config_revalidated_at_use_even_for_empty_input(field: str, value: object) -> None:
    chosen = config()
    object.__setattr__(chosen, field, value)
    with pytest.raises(ValueError, match=field):
        ranking.rank_candidates([], chosen, {})
    with pytest.raises(ValueError, match=field):
        ranking.score_candidate(item(), chosen)


@pytest.mark.parametrize("travel,expected", [(0, 0), (30, 0.5), (60, 2 / 3)])
def test_travel_normalization(travel: float, expected: float) -> None:
    assert ranking.normalize_travel_time(travel, 30) == pytest.approx(expected)


def test_normalizations_do_not_overflow_or_depend_on_list_extrema() -> None:
    assert ranking.normalize_travel_time(1e308, 1e308) == pytest.approx(0.5)
    assert ranking.normalize_virtual_load(1e308, 10**308) == pytest.approx(0.5)
    assert 0 <= ranking.normalize_travel_time(1e308, 30) < 1
    assert 0 <= ranking.normalize_virtual_load(1e308, 2) < 1


@pytest.mark.parametrize(
    "soc_value,expected", [(10, 1), (10.001, 0.99995), (20, 0.5), (30, 0), (100, 0)]
)
def test_soc_risk_normalization(soc_value: float, expected: float) -> None:
    assert ranking.normalize_soc_risk(soc_value, 10, 20) == pytest.approx(expected)


def test_soc_risk_tiny_band_and_threshold_endpoints() -> None:
    assert ranking.normalize_soc_risk(10, 10, 1e-300) == 1
    assert ranking.normalize_soc_risk(0, 0, 20) == 1
    assert ranking.normalize_soc_risk(100, 100, 20) == 1


@pytest.mark.parametrize(
    "load,ports,expected", [(0, 2, 0), (2, 2, 0.5), (6, 2, 0.75), (2, 6, 0.25)]
)
def test_capacity_relative_virtual_load(load: float, ports: int, expected: float) -> None:
    assert ranking.normalize_virtual_load(load, ports) == pytest.approx(expected)


def test_score_breakdown_uses_hand_calculated_four_component_formula() -> None:
    chosen = config(weight_travel=0.2, weight_soc_risk=0.2, weight_virtual_load=0.3)
    breakdown = ranking.score_candidate(item(arrival_soc=20), chosen, 2)
    assert breakdown.probability == 0.8
    assert breakdown.normalized_travel_time == 0.5
    assert breakdown.normalized_soc_risk == 0.5
    assert breakdown.normalized_virtual_load == 0.5
    assert breakdown.score == pytest.approx(0.45)
    ranked = ranking.rank_candidates([item(arrival_soc=20)], chosen, {"S001": 2})
    assert ranked[0].score == breakdown.score
    with pytest.raises(FrozenInstanceError):
        setattr(breakdown, "score", 1)


@pytest.mark.parametrize("dimension", ["probability", "travel", "soc", "load"])
def test_changing_one_input_only_changes_its_breakdown_component(dimension: str) -> None:
    original = item(arrival_soc=20)
    changed = item(probability=0.9, arrival_soc=20) if dimension == "probability" else original
    if dimension == "travel":
        changed = replace(original, travel_minutes=60)
    if dimension == "soc":
        changed = item(arrival_soc=30)
    before = ranking.score_candidate(original, config(), 2)
    after = ranking.score_candidate(changed, config(), 6 if dimension == "load" else 2)
    component = {
        "probability": "probability",
        "travel": "normalized_travel_time",
        "soc": "normalized_soc_risk",
        "load": "normalized_virtual_load",
    }[dimension]
    for name in (
        "probability",
        "normalized_travel_time",
        "normalized_soc_risk",
        "normalized_virtual_load",
    ):
        assert (getattr(before, name) != getattr(after, name)) is (name == component)


def test_higher_probability_and_boundaries_rank_first() -> None:
    entries = [item("A", probability=0), item("B", probability=0.85), item("C", probability=1)]
    result = ranking.rank_candidates(entries, config(), {})
    assert [ranked.station_id for ranked in result] == ["C", "B", "A"]
    assert [ranked.p_available for ranked in result] == [1, 0.85, 0]
    assert [ranked.rank for ranked in result] == [1, 2, 3]
    assert all(isinstance(ranked, RankedCandidate) for ranked in result)


def test_actual_travel_time_not_distance_controls_penalty() -> None:
    entries = [item("slow", travel=60, distance=1), item("fast", travel=0, distance=100)]
    chosen = config(weight_probability=0, weight_travel=1)
    result = ranking.rank_candidates(entries, chosen, {})
    assert [ranked.station_id for ranked in result] == ["fast", "slow"]
    assert result[0].score == 0


def test_soc_and_virtual_load_penalties_change_order() -> None:
    soc_entries = [item("risk", arrival_soc=10), item("safe", arrival_soc=30)]
    assert (
        ranking.rank_candidates(soc_entries, config(weight_soc_risk=1), {})[0].station_id == "safe"
    )
    load_entries = [item("small", ports=2), item("large", ports=6)]
    loads = {"small": 2, "large": 2}
    assert (
        ranking.rank_candidates(load_entries, config(weight_virtual_load=1), loads)[0].station_id
        == "large"
    )


@pytest.mark.parametrize(
    "weight", ["weight_probability", "weight_travel", "weight_soc_risk", "weight_virtual_load"]
)
def test_configurable_weights_predictably_reverse_ranking(weight: str) -> None:
    if weight in ("weight_probability", "weight_travel"):
        entries = [item("high", probability=0.9, travel=30), item("low", probability=0.5, travel=0)]
    elif weight == "weight_soc_risk":
        entries = [item("high", probability=0.9, arrival_soc=10), item("low", probability=0.5)]
    else:
        entries = [item("high", probability=0.9), item("low", probability=0.5)]
    loads = {"high": 2} if weight == "weight_virtual_load" else {}
    before = (
        config(weight_probability=0.2, weight_travel=1)
        if weight == "weight_probability"
        else config()
    )
    after = (
        config(weight_probability=2, weight_travel=1)
        if weight == "weight_probability"
        else config(**{weight: 1})
    )
    expected_before = "low" if weight == "weight_probability" else "high"
    expected_after = "high" if weight == "weight_probability" else "low"
    assert ranking.rank_candidates(entries, before, loads)[0].station_id == expected_before
    assert ranking.rank_candidates(entries, after, loads)[0].station_id == expected_after


def test_zero_weights_disable_penalties_without_hiding_components() -> None:
    chosen = config()
    breakdown = ranking.score_candidate(item(travel=300, arrival_soc=10), chosen, 100)
    assert breakdown.score == breakdown.probability == 0.8
    assert breakdown.normalized_travel_time > 0
    assert breakdown.normalized_soc_risk == 1
    assert breakdown.normalized_virtual_load > 0


def test_custom_normalization_parameters_change_sensitivity() -> None:
    selected = item(arrival_soc=20)
    assert ranking.score_candidate(
        selected, config(travel_reference_minutes=60)
    ).normalized_travel_time == pytest.approx(1 / 3)
    assert (
        ranking.score_candidate(selected, config(soc_risk_band_pct=40)).normalized_soc_risk == 0.75
    )
    assert (
        ranking.score_candidate(selected, config(min_arrival_soc_pct=20)).normalized_soc_risk == 1
    )


def test_exact_ties_are_lexicographic_and_reordering_cannot_change_ranks() -> None:
    entries = [item("S003"), item("S001"), item("S002")]
    expected = ranking.rank_candidates(entries, config(), {})
    assert [ranked.station_id for ranked in expected] == ["S001", "S002", "S003"]
    for reordered in permutations(entries):
        assert ranking.rank_candidates(iter(reordered), config(), {}) == expected


def test_near_scores_are_not_rounded_into_ties() -> None:
    result = ranking.rank_candidates(
        [item("A", probability=0.8), item("Z", probability=0.800000000001)], config(), {}
    )
    assert result[0].station_id == "Z"


def test_empty_input_and_duplicate_ids() -> None:
    assert ranking.rank_candidates([], config(), {}) == ()
    with pytest.raises(ValueError, match="duplicate"):
        ranking.rank_candidates([item(), item()], config(), {})


def test_inputs_are_unchanged_and_missing_load_is_zero() -> None:
    entries = [item("A", probability=0.851234567890123), item("B", probability=0.75)]
    before = [entry.candidate.model_dump() for entry in entries]
    chosen = config(weight_virtual_load=2)
    config_before = asdict(chosen)
    loads = {"A": 1000.0}
    snapshot = MappingProxyType(loads)
    result = ranking.rank_candidates(entries, chosen, snapshot)
    assert result == ranking.rank_candidates(entries, chosen, snapshot)
    assert [entry.candidate.model_dump() for entry in entries] == before
    assert asdict(chosen) == config_before
    assert loads == {"A": 1000.0}
    assert {entry.station_id: entry.p_available for entry in result} == {
        "A": 0.851234567890123,
        "B": 0.75,
    }
    assert ranking.score_candidate(entries[1], chosen).normalized_virtual_load == 0
    assert ranking.rank_candidates([entries[1]], chosen, {}) == ranking.rank_candidates(
        [entries[1]], chosen, {"B": 0}
    )
    assert result[1].score < 0
    result[0].p_available = 0.01
    assert entries[1].candidate.p_available == 0.75


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), -float("inf"), True, "1", None])
def test_invalid_travel_and_load_rejected_even_if_disabled(value: object) -> None:
    with pytest.raises(ValueError, match="travel"):
        ranking.rank_candidates([replace(item(), travel_minutes=value)], config(), {})
    with pytest.raises(ValueError, match="virtual_load"):
        ranking.rank_candidates([item()], config(), {"S001": cast(Any, value)})
    with pytest.raises(ValueError, match="virtual_load"):
        ranking.score_candidate(item(), config(), cast(Any, value))


@pytest.mark.parametrize("value", [0, -1, 1.5, True, "2", None])
def test_invalid_capacity_never_gets_rank(value: object) -> None:
    with pytest.raises(ValueError, match="working_ports"):
        ranking.rank_candidates([replace(item(), working_ports=value)], config(), {})


@pytest.mark.parametrize("field", ["p_available", "arrival_soc_pct", "distance_km", "detour_km"])
@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), -float("inf"), True, "1", None])
def test_mutated_candidate_numeric_fields_revalidated(field: str, value: object) -> None:
    selected = item()
    setattr(selected.candidate, field, value)
    with pytest.raises(ValueError, match=field):
        ranking.rank_candidates([selected], config(), {})
    with pytest.raises(ValueError, match=field):
        ranking.score_candidate(selected, config())


@pytest.mark.parametrize(
    "field,value",
    [
        ("p_available", 1.01),
        ("arrival_soc_pct", 101),
        ("arrival_soc_pct", 9.999),
        ("station_id", ""),
        ("station_id", None),
        ("eta", datetime(2026, 10, 13)),
        ("eta", None),
    ],
)
def test_mutated_candidate_bounds_and_identity_revalidated(field: str, value: object) -> None:
    selected = item()
    setattr(selected.candidate, field, value)
    with pytest.raises(ValueError, match=field):
        ranking.rank_candidates([selected], config(), {})


def test_invalid_unused_load_and_wrong_input_types_are_explicit_errors() -> None:
    with pytest.raises(ValueError, match="virtual_load"):
        ranking.rank_candidates([], config(), {"unused": -1})
    with pytest.raises(ValueError, match="station_id"):
        ranking.rank_candidates([], config(), {"": 0})
    with pytest.raises(ValueError, match="RankingInput"):
        ranking.rank_candidates([cast(Any, None)], config(), {})
    with pytest.raises(ValueError, match="candidate"):
        ranking.rank_candidates([replace(item(), candidate=None)], config(), {})


def test_nonfinite_score_rejected_despite_finite_weights() -> None:
    chosen = config(weight_travel=1.7e308, weight_soc_risk=1.7e308, weight_virtual_load=1.7e308)
    with pytest.raises(ValueError, match="score"):
        ranking.rank_candidates([item(travel=300, arrival_soc=10)], chosen, {"S001": 100})


def test_public_exports_and_default_config_produce_finite_ranking() -> None:
    from app.backend.modules import recommendation

    result = ranking.rank_candidates([item()], ranking.RankingConfig(), {})
    assert isfinite(result[0].score)
    for name in (
        "RankingConfig",
        "RankingInput",
        "RankingBreakdown",
        "rank_candidates",
        "score_candidate",
        "normalize_travel_time",
        "normalize_soc_risk",
        "normalize_virtual_load",
    ):
        assert getattr(recommendation, name) is getattr(ranking, name)


def test_already_ranked_candidate_rejected_explicitly_without_mutation() -> None:
    selected = item()
    ranked = ranking.rank_candidates([selected], config(), {})[0]
    before = ranked.model_dump()
    already_ranked = replace(selected, candidate=ranked)
    with pytest.raises(ValueError, match="unranked FeasibleCandidate") as rank_error:
        ranking.rank_candidates([already_ranked], config(), {})
    with pytest.raises(ValueError, match="unranked FeasibleCandidate") as score_error:
        ranking.score_candidate(already_ranked, config())
    assert type(rank_error.value) is ValueError
    assert type(score_error.value) is ValueError
    assert ranked.model_dump() == before
    assert ranking.rank_candidates([selected], config(), {}) == (ranked,)
    assert ranking.score_candidate(selected, config()).score == ranked.score


@pytest.mark.parametrize(
    "field",
    [
        "weight_probability",
        "weight_travel",
        "weight_soc_risk",
        "weight_virtual_load",
        "travel_reference_minutes",
        "min_arrival_soc_pct",
        "soc_risk_band_pct",
    ],
)
def test_huge_integer_config_fields_raise_controlled_errors(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        config(**{field: 10**10000})


def test_huge_integer_measurements_raise_controlled_public_errors() -> None:
    huge = 10**10000
    chosen = config()
    with pytest.raises(ValueError, match="travel_minutes"):
        ranking.rank_candidates([replace(item(), travel_minutes=huge)], chosen, {})
    with pytest.raises(ValueError, match="travel_minutes"):
        ranking.score_candidate(replace(item(), travel_minutes=huge), chosen)
    with pytest.raises(ValueError, match="virtual_load"):
        ranking.rank_candidates([item()], chosen, {"S001": huge})
    with pytest.raises(ValueError, match="virtual_load"):
        ranking.score_candidate(item(), chosen, huge)
    with pytest.raises(ValueError, match="working_ports"):
        ranking.rank_candidates([replace(item(), working_ports=huge)], chosen, {})
    with pytest.raises(ValueError, match="travel_reference_minutes"):
        ranking.normalize_travel_time(30, huge)
    with pytest.raises(ValueError, match="travel_minutes"):
        ranking.normalize_travel_time(huge, 30)
    with pytest.raises(ValueError, match="soc_risk_band_pct"):
        ranking.normalize_soc_risk(30, 10, huge)
    with pytest.raises(ValueError, match="min_arrival_soc_pct"):
        ranking.normalize_soc_risk(30, huge, 20)
    with pytest.raises(ValueError, match="virtual_load"):
        ranking.normalize_virtual_load(huge, 2)
    with pytest.raises(ValueError, match="working_ports"):
        ranking.normalize_virtual_load(2, huge)


@pytest.mark.parametrize("invalid_config", ["invalid", None, {}, object()])
def test_invalid_config_type_rejected_before_reading_fields(invalid_config: object) -> None:
    invalid = cast(Any, invalid_config)
    with pytest.raises(ValueError, match="config must be a RankingConfig"):
        ranking.rank_candidates([item()], invalid, {})
    with pytest.raises(ValueError, match="config must be a RankingConfig"):
        ranking.rank_candidates([], invalid, {})
    with pytest.raises(ValueError, match="config must be a RankingConfig"):
        ranking.score_candidate(item(), invalid)


def test_direct_soc_normalization_rejects_below_threshold_not_clamps() -> None:
    with pytest.raises(ValueError, match="arrival_soc_pct must meet min_arrival_soc_pct"):
        ranking.normalize_soc_risk(9.999, 10, 20)
    assert ranking.normalize_soc_risk(10, 10, 20) == 1
    assert ranking.normalize_soc_risk(10.001, 10, 20) == pytest.approx(0.99995)
    assert ranking.normalize_soc_risk(30, 10, 20) == 0


def test_matching_custom_minimum_soc_is_required_for_ranking() -> None:
    selected = item(arrival_soc=8)
    chosen = config(min_arrival_soc_pct=5)
    assert ranking.score_candidate(selected, chosen).normalized_soc_risk == pytest.approx(0.85)
    result = ranking.rank_candidates([selected], chosen, {})
    assert result[0].arrival_soc_pct == 8
    assert result[0].p_available == selected.candidate.p_available
    with pytest.raises(ValueError, match="arrival_soc_pct must meet min_arrival_soc_pct"):
        ranking.rank_candidates([selected], ranking.RankingConfig(), {})
