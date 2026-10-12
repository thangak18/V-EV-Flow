"""Feature contract, time-boundary, and train-only imputation tests."""

import json
from pathlib import Path
from typing import cast

import pandas as pd
import pytest

from app.backend.contracts.stations import Station
from app.backend.modules.prediction.dataset import validate_status_frame
from app.backend.modules.prediction.features import FEATURE_COLUMNS, FeatureBuilder
from app.backend.modules.prediction.labels import build_labels


@pytest.fixture
def stations() -> tuple[Station, ...]:
    path = Path(__file__).parents[2] / "station_data" / "fixtures" / "stations.json"
    return tuple(Station.model_validate(row) for row in json.loads(path.read_text()))


@pytest.fixture
def histories(stations: tuple[Station, ...]) -> pd.DataFrame:
    rows = []
    for scenario, station_id in (("normal", "S001"), ("normal", "S002"), ("tet", "S001")):
        for minute in range(0, 95, 5):
            if scenario == "normal" and station_id == "S001" and minute == 30:
                continue  # Exactly 08:30 is missing: no positional shifts.
            capacity = 6 if station_id == "S002" else 4
            free = (minute // 5) % 5 if station_id == "S001" else 2
            if scenario == "tet":
                free = 0
            free = min(capacity, free)
            rows.append(
                {
                    "station_id": station_id,
                    "ts": pd.Timestamp("2026-10-13T08:00:00+07:00") + pd.Timedelta(minutes=minute),
                    "ports_free": free,
                    "ports_busy": capacity - free,
                    "ports_broken": 0,
                    "scenario": scenario,
                }
            )
    return validate_status_frame(pd.DataFrame(rows).sample(frac=1, random_state=42), stations)


@pytest.fixture
def labels(histories: pd.DataFrame) -> pd.DataFrame:
    return build_labels(histories, [15, 5])


def row_for(
    features: pd.DataFrame, clock: str, scenario: str = "normal", station: str = "S001"
) -> pd.Series:
    matching = features.loc[
        (features["station_id"] == station)
        & (features["scenario"] == scenario)
        & (features["observed_at"] == pd.Timestamp(f"2026-10-13T{clock}:00+07:00"))
        & (features["horizon_minutes"] == 5)
    ]
    assert len(matching) == 1
    return matching.iloc[0]


def test_builder_must_be_fitted_on_training_data_first(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="fit|training"):
        FeatureBuilder(stations).build(histories, labels)


def test_lags_match_exact_historical_timestamps_and_mark_gaps(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    result = FeatureBuilder(stations).fit(histories, labels).build(histories, labels)
    at_0845 = row_for(result.frame, "08:45")
    assert at_0845["ports_free"] == 4
    assert at_0845["ports_free_lag_30"] == 3  # 08:15, not 08:10.
    assert at_0845["lag_15_missing"] == 1  # 08:30 absent; do not shift from 08:25.
    assert at_0845["lag_30_missing"] == 0
    at_0900 = row_for(result.frame, "09:00")
    assert at_0900["ports_free_lag_60"] == 0  # 08:00
    assert at_0900["lag_60_missing"] == 0


def test_missing_lags_are_explicit_even_if_free_ports_are_zero(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    result = FeatureBuilder(stations).fit(histories, labels).build(histories, labels)
    early = row_for(result.frame, "08:05")
    assert early["lag_15_missing"] == 1
    assert early["lag_30_missing"] == 1
    assert early["lag_60_missing"] == 1
    at_0815 = row_for(result.frame, "08:15")
    assert at_0815["ports_free_lag_15"] == 0
    assert at_0815["lag_15_missing"] == 0


def test_lag_lookup_is_isolated_by_scenario_and_station(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    result = FeatureBuilder(stations).fit(histories, labels).build(histories, labels)
    at_0845_tet = row_for(result.frame, "08:45", scenario="tet")
    at_0845_s002 = row_for(result.frame, "08:45", station="S002")
    assert at_0845_tet["ports_free_lag_15"] == 0
    assert at_0845_tet["lag_15_missing"] == 0
    assert at_0845_s002["ports_free_lag_15"] == 2
    assert at_0845_s002["lag_15_missing"] == 0


def test_model_frame_is_numeric_and_feature_order_is_fixed(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    result = FeatureBuilder(stations).fit(histories, labels).build(histories, labels)
    assert list(result.X.columns) == list(FEATURE_COLUMNS)
    assert all(pd.api.types.is_numeric_dtype(dtype) for dtype in result.X.dtypes)
    assert not bool(result.X.isna().any().any())
    assert list(result.frame.loc[:, list(FEATURE_COLUMNS)].columns) == list(FEATURE_COLUMNS)
    assert result.y.equals(result.frame["target_available"])
    assert set(result.y.unique()) == {0, 1}
    assert row_for(result.frame, "08:45")["horizon_minutes"] == 5
    assert row_for(result.frame, "08:45")["n_ports"] == 4
    assert row_for(result.frame, "08:45")["power_kw"] == 120
    assert row_for(result.frame, "08:45", station="S002")["n_ports"] == 6
    assert row_for(result.frame, "08:45")["scenario_normal"] == 1
    assert row_for(result.frame, "08:45", scenario="tet")["scenario_tet"] == 1
    assert row_for(result.frame, "08:45", scenario="tet")["is_holiday_scenario"] == 1
    assert row_for(result.frame, "08:45")["hour_sin"] == pytest.approx(0.75183981, abs=1e-7)


def test_training_only_medians_reused_without_refitting(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    subset = cast(
        pd.DataFrame, labels[(labels["scenario"] == "normal") & (labels["station_id"] == "S001")]
    )
    training = cast(
        pd.DataFrame, subset[subset["observed_at"] <= pd.Timestamp("2026-10-13T08:25:00+07:00")]
    )
    builder = FeatureBuilder(stations).fit(histories, training)
    median = builder.lag_fill_values["ports_free_lag_15"]
    assert median == pytest.approx(1.0)  # lag snapshots: 08:00=0, 08:05=1, 08:10=2

    eval_labels = cast(
        pd.DataFrame, subset[subset["observed_at"] == pd.Timestamp("2026-10-13T08:45:00+07:00")]
    )
    frame = builder.build(histories, eval_labels).frame
    assert frame.iloc[0]["ports_free_lag_15"] == median  # 08:30 is missing.
    assert frame.iloc[0]["lag_15_missing"] == 1
    assert builder.lag_fill_values["ports_free_lag_15"] == median


def test_all_missing_training_lag_has_deterministic_zero_fallback(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    early = cast(
        pd.DataFrame, labels[labels["observed_at"] == pd.Timestamp("2026-10-13T08:00:00+07:00")]
    )
    builder = FeatureBuilder(stations).fit(histories, early)
    assert builder.lag_fill_values["ports_free_lag_60"] == 0
    future = cast(
        pd.DataFrame, labels[labels["observed_at"] == pd.Timestamp("2026-10-13T08:05:00+07:00")]
    )
    result = builder.build(histories, future)
    assert (result.X["lag_60_missing"] == 1).all()
    assert (result.X["ports_free_lag_60"] == 0).all()


def test_future_snapshots_and_target_values_cannot_leak_into_features(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    training = cast(
        pd.DataFrame, labels[labels["observed_at"] <= pd.Timestamp("2026-10-13T08:20:00+07:00")]
    )
    evaluated = cast(
        pd.DataFrame, labels[labels["observed_at"] == pd.Timestamp("2026-10-13T08:45:00+07:00")]
    )
    builder = FeatureBuilder(stations).fit(histories, training)
    original = builder.build(histories, evaluated).X
    changed_future = histories.copy(deep=True)
    changed_future.loc[
        changed_future["ts"] > pd.Timestamp("2026-10-13T08:45:00+07:00"), "ports_free"
    ] = 777
    altered_targets = evaluated.copy(deep=True)
    altered_targets["target_available"] = 1 - altered_targets["target_available"]
    comparison = builder.build(changed_future, altered_targets).X
    pd.testing.assert_frame_equal(original, comparison)


def test_shuffle_and_label_horizon_order_does_not_change_output(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    builder = FeatureBuilder(stations).fit(histories, labels)
    first = builder.build(histories, labels)
    shuffled = builder.build(
        histories.sample(frac=1, random_state=11), labels.sample(frac=1, random_state=99)
    )
    pd.testing.assert_frame_equal(first.frame, shuffled.frame)
    pd.testing.assert_frame_equal(first.X, shuffled.X)


def test_does_not_mutate_status_labels_or_station_metadata(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    before_status = histories.copy(deep=True)
    before_labels = labels.copy(deep=True)
    before_station = [station.model_dump() for station in stations]
    FeatureBuilder(stations).fit(histories, labels).build(histories, labels)
    pd.testing.assert_frame_equal(histories, before_status)
    pd.testing.assert_frame_equal(labels, before_labels)
    assert [station.model_dump() for station in stations] == before_station


def test_rejects_labels_without_matching_observed_status(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    builder = FeatureBuilder(stations).fit(histories, labels)
    corrupted = labels.iloc[:1].copy()
    corrupted["station_id"] = "S404"
    with pytest.raises(ValueError, match="observed|station"):
        builder.build(histories, corrupted)


def test_rejects_duplicate_label_keys_and_duplicate_station_metadata(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="duplicate"):
        FeatureBuilder((*stations, stations[0]))
    builder = FeatureBuilder(stations).fit(histories, labels)
    duplicated = pd.concat([labels.iloc[:1], labels.iloc[:1]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        builder.build(histories, duplicated)


def test_rejects_unrecognized_labels_and_empty_training_split(
    stations: tuple[Station, ...], histories: pd.DataFrame, labels: pd.DataFrame
) -> None:
    with pytest.raises(ValueError, match="empty|training"):
        FeatureBuilder(stations).fit(histories, labels.iloc[0:0])
    builder = FeatureBuilder(stations).fit(histories, labels)
    with pytest.raises(ValueError, match="columns"):
        builder.build(histories, labels.drop(columns="eta"))
