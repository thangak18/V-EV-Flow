"""Availability labels must use the exact future station/scenario snapshot."""

from collections.abc import Sequence
from typing import cast

import numpy as np
import pandas as pd
import pytest

from app.backend.modules.prediction.labels import build_labels


@pytest.fixture
def status_frame() -> pd.DataFrame:
    # The normal S001 timeline deliberately skips 08:20.
    rows = [
        ("S001", "normal", "08:25", 0),
        ("S002", "normal", "08:00", 0),
        ("S001", "tet", "08:10", 0),
        ("S001", "normal", "08:00", 4),
        ("S001", "normal", "08:15", 1),
        ("S002", "normal", "08:10", 0),
        ("S001", "tet", "08:05", 1),
        ("S001", "normal", "08:10", 2),
        ("S001", "tet", "08:00", 0),
        ("S002", "normal", "08:05", 2),
        ("S001", "normal", "08:05", 0),
    ]
    return pd.DataFrame(
        [
            {
                "station_id": station,
                "ts": pd.Timestamp(f"2026-10-13T{clock}:00+07:00"),
                "ports_free": free,
                "ports_busy": (6 if station == "S002" else 4) - free,
                "ports_broken": 0,
                "scenario": scenario,
            }
            for station, scenario, clock, free in rows
        ]
    )


def find_label(
    labels: pd.DataFrame, station: str, scenario: str, observed: str, horizon: int
) -> pd.Series:
    mask = (
        (labels["station_id"] == station)
        & (labels["scenario"] == scenario)
        & (labels["observed_at"] == pd.Timestamp(f"2026-10-13T{observed}:00+07:00"))
        & (labels["horizon_minutes"] == horizon)
    )
    rows = labels.loc[mask]
    assert len(rows) == 1
    return rows.iloc[0]


def test_uses_exact_future_availability_not_current_availability(
    status_frame: pd.DataFrame,
) -> None:
    labels = build_labels(status_frame, [5])
    assert find_label(labels, "S001", "normal", "08:00", 5)["target_available"] == 0
    assert find_label(labels, "S001", "normal", "08:05", 5)["target_available"] == 1
    assert find_label(labels, "S001", "tet", "08:00", 5)["target_available"] == 1
    assert set(labels["target_available"].unique()) == {0, 1}


def test_never_crosses_station_or_scenario_boundaries(status_frame: pd.DataFrame) -> None:
    labels = build_labels(status_frame, [5])
    assert find_label(labels, "S002", "normal", "08:00", 5)["target_available"] == 1
    assert find_label(labels, "S001", "tet", "08:05", 5)["target_available"] == 0
    # The last S002 timestamp must not borrow future rows from S001.
    assert not ((labels["station_id"] == "S002") & (labels["observed_at"].dt.minute == 10)).any()


def test_matches_exact_eta_across_missing_intermediate_snapshot(
    status_frame: pd.DataFrame,
) -> None:
    # 08:20 is missing, but 08:15 + 10 min = 08:25 is present.
    labels = build_labels(status_frame, [10])
    row = find_label(labels, "S001", "normal", "08:15", 10)
    assert row["eta"] == pd.Timestamp("2026-10-13T08:25:00+07:00")
    assert row["target_available"] == 0


def test_drops_missing_exact_future_timestamp_instead_of_using_nearest(
    status_frame: pd.DataFrame,
) -> None:
    labels = build_labels(status_frame, [5])
    missing = (
        (labels["station_id"] == "S001")
        & (labels["scenario"] == "normal")
        & (labels["observed_at"] == pd.Timestamp("2026-10-13T08:15:00+07:00"))
    )
    assert not missing.any()
    assert all(
        eta - observed == pd.Timedelta(minutes=5)
        for eta, observed in zip(labels["eta"], labels["observed_at"], strict=True)
    )


def test_multiple_horizons_sorted_deterministically_and_no_input_mutation(
    status_frame: pd.DataFrame,
) -> None:
    original = status_frame.copy(deep=True)
    result = build_labels(status_frame, [15, 5, 10])
    pd.testing.assert_frame_equal(status_frame, original)

    assert list(result.columns) == [
        "station_id",
        "scenario",
        "observed_at",
        "eta",
        "horizon_minutes",
        "target_available",
    ]
    assert result["observed_at"].dt.tz is not None
    assert result["eta"].dt.tz is not None
    assert set(result["horizon_minutes"]) == {5, 10, 15}
    assert result["target_available"].dtype.kind in "iu"
    assert result["horizon_minutes"].dtype.kind in "iu"
    pd.testing.assert_frame_equal(
        result,
        result.sort_values(
            ["scenario", "station_id", "observed_at", "horizon_minutes"],
            kind="mergesort",
        ).reset_index(drop=True),
    )
    pd.testing.assert_frame_equal(
        result, build_labels(status_frame.sample(frac=1, random_state=42), [10, 5, 15])
    )


def test_no_matching_eta_returns_empty_frame_with_output_columns(
    status_frame: pd.DataFrame,
) -> None:
    result = build_labels(status_frame, [120])
    assert result.empty
    assert list(result.columns) == [
        "station_id",
        "scenario",
        "observed_at",
        "eta",
        "horizon_minutes",
        "target_available",
    ]


@pytest.mark.parametrize("invalid", [0, -5, 6, 7, 1.5, "5", True, None, np.bool_(True)])
def test_rejects_nonpositive_nongrid_or_noninteger_horizon(
    status_frame: pd.DataFrame, invalid: object
) -> None:
    with pytest.raises(ValueError, match="horizon"):
        build_labels(status_frame, cast(Sequence[int], [invalid]))


def test_rejects_empty_and_duplicate_horizon_configuration(status_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="horizon"):
        build_labels(status_frame, [])
    with pytest.raises(ValueError, match="duplicate|horizon"):
        build_labels(status_frame, [5, 5])


def test_accepts_numpy_integer_horizon(status_frame: pd.DataFrame) -> None:
    labels = build_labels(status_frame, cast(Sequence[int], [np.int64(5)]))
    assert len(labels) > 0


def test_rejects_invalid_schema_and_duplicate_keys(status_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="columns"):
        build_labels(status_frame.drop(columns="ts"), [5])
    duplicated = pd.concat([status_frame, status_frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate|unique"):
        build_labels(duplicated, [5])


def test_requires_validated_timezone_aware_timestamps(status_frame: pd.DataFrame) -> None:
    unvalidated = status_frame.copy()
    unvalidated["ts"] = unvalidated["ts"].dt.tz_localize(None)
    with pytest.raises(ValueError, match="timezone|validated|ts"):
        build_labels(unvalidated, [5])
