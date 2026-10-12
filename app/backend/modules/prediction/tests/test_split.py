"""Global chronological splitting, embargo, and aligned matrix tests."""

import json
from pathlib import Path
from typing import cast

import pandas as pd
import pytest

from app.backend.contracts.stations import Station
from app.backend.modules.prediction.dataset import validate_status_frame
from app.backend.modules.prediction.features import FeatureBuilder, FeatureDataset
from app.backend.modules.prediction.labels import build_labels
from app.backend.modules.prediction.split import DatasetSplit, temporal_split


def at(hour: int, minute: int = 0) -> pd.Timestamp:
    return cast(pd.Timestamp, pd.Timestamp(f"2026-10-13T{hour:02d}:{minute:02d}:00+07:00"))


@pytest.fixture
def stations() -> tuple[Station, ...]:
    path = Path(__file__).parents[2] / "station_data" / "fixtures" / "stations.json"
    # Row-count assertions below assume two stations; the fixture may hold more.
    return tuple(Station.model_validate(row) for row in json.loads(path.read_text()))[:2]


@pytest.fixture
def status(stations: tuple[Station, ...]) -> pd.DataFrame:
    start = at(8)
    rows = []
    for scenario in ("normal", "tet"):
        for station in stations:
            for minutes in range(0, 8 * 60 + 5, 5):
                free = (minutes // 5) % (station.n_ports + 1)
                if scenario == "tet":
                    free = 0
                rows.append(
                    {
                        "station_id": station.station_id,
                        "scenario": scenario,
                        "ts": start + pd.Timedelta(minutes=minutes),
                        "ports_free": free,
                        "ports_busy": station.n_ports - free,
                        "ports_broken": 0,
                    }
                )
    return validate_status_frame(pd.DataFrame(rows), stations)


@pytest.fixture
def labels(status: pd.DataFrame) -> pd.DataFrame:
    return build_labels(status, [5, 15, 60])


def test_global_split_purges_max_horizon_and_prevents_eta_overlap(labels: pd.DataFrame) -> None:
    split = temporal_split(labels, at(10), at(12), 60)
    assert isinstance(split, DatasetSplit)
    assert split.train["eta"].max() < split.calibration["observed_at"].min()
    assert split.calibration["eta"].max() < split.test["observed_at"].min()
    assert split.train["observed_at"].max() == at(9)
    assert split.calibration["observed_at"].min() == at(10, 5)
    assert split.calibration["observed_at"].max() == at(11)
    assert split.test["observed_at"].min() == at(12, 5)
    assert split.metadata.max_horizon_minutes == 60
    assert split.metadata.train_end == at(10)
    assert split.metadata.calibration_end == at(12)
    assert split.metadata.counts == {
        "train": len(split.train),
        "calibration": len(split.calibration),
        "test": len(split.test),
    }
    assert split.metadata.dropped_for_embargo == {"train": 12 * 4 * 3, "calibration": 12 * 4 * 3}
    assert sum(split.metadata.counts.values()) + sum(
        split.metadata.dropped_for_embargo.values()
    ) == len(labels)


def test_short_horizon_rows_are_also_embargoed(labels: pd.DataFrame) -> None:
    split = temporal_split(labels, at(10), at(12), 60)
    # Even a 5-minute label at 09:55 is removed: all horizons share the same split gap.
    for part in (split.train, split.calibration):
        assert at(9, 55) not in set(part["observed_at"])
        assert at(11, 55) not in set(part["observed_at"])
    assert at(10, 5) in set(split.calibration["observed_at"])
    assert at(12, 5) in set(split.test["observed_at"])


def test_partition_sort_and_metadata_are_deterministic(labels: pd.DataFrame) -> None:
    one = temporal_split(labels, at(10), at(12), 60)
    two = temporal_split(labels.sample(frac=1, random_state=23), at(10), at(12), 60)
    for name in ("train", "calibration", "test"):
        pd.testing.assert_frame_equal(getattr(one, name), getattr(two, name))
        assert getattr(one, name).index.equals(pd.RangeIndex(len(getattr(one, name))))
    assert one.metadata == two.metadata
    assert one.metadata.observed_ranges["train"] == (at(8), at(9))


def test_feature_dataset_remains_aligned_and_training_fit_is_separate(
    stations: tuple[Station, ...], status: pd.DataFrame, labels: pd.DataFrame
) -> None:
    raw = temporal_split(labels, at(10), at(12), 60)
    builder = FeatureBuilder(stations).fit(status, raw.train)
    features = builder.build(status, labels)
    split = temporal_split(features, at(10), at(12), 60)
    for partition, raw_labels in (
        (split.train, raw.train),
        (split.calibration, raw.calibration),
        (split.test, raw.test),
    ):
        assert isinstance(partition, FeatureDataset)
        assert len(partition.frame) == len(partition.X) == len(partition.y) == len(raw_labels)
        assert partition.y.equals(partition.frame["target_available"])
        pd.testing.assert_frame_equal(partition.X, partition.frame.loc[:, list(features.X.columns)])
        assert partition.frame["observed_at"].equals(raw_labels["observed_at"])
    assert split.metadata == raw.metadata


def test_does_not_mutate_frames_features_or_labels(
    stations: tuple[Station, ...], status: pd.DataFrame, labels: pd.DataFrame
) -> None:
    original = labels.copy(deep=True)
    builder = FeatureBuilder(stations).fit(status, temporal_split(labels, at(10), at(12), 60).train)
    dataset = builder.build(status, labels)
    old_frame, old_x, old_y = (dataset.frame.copy(), dataset.X.copy(), dataset.y.copy())
    temporal_split(dataset, at(10), at(12), 60)
    temporal_split(labels, at(10), at(12), 60)
    pd.testing.assert_frame_equal(labels, original)
    pd.testing.assert_frame_equal(dataset.frame, old_frame)
    pd.testing.assert_frame_equal(dataset.X, old_x)
    pd.testing.assert_series_equal(dataset.y, old_y)


@pytest.mark.parametrize(
    "train_end,cal_end,max_horizon,error",
    [
        ("2026-10-13T10:00:00", at(12), 60, "timezone"),
        (at(10), "2026-10-13T12:00:00", 60, "timezone"),
        (at(12), at(10), 60, "before"),
        (at(10), at(10), 60, "before"),
        (at(10), at(12), 0, "horizon"),
        (at(10), at(12), 7, "horizon"),
        (at(10), at(12), True, "horizon"),
        (at(10), at(12), 15, "horizon"),
        (at(10), at(12), 300, "empty"),
    ],
)
def test_rejects_bad_cutoffs_gap_and_empty_partition(
    labels: pd.DataFrame, train_end: object, cal_end: object, max_horizon: object, error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        temporal_split(labels, train_end, cal_end, max_horizon)


def test_rejects_corrupted_labels_and_duplicate_keys(labels: pd.DataFrame) -> None:
    dup = pd.concat([labels, labels.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        temporal_split(dup, at(10), at(12), 60)
    invalid = labels.copy()
    invalid.loc[0, "eta"] = invalid.loc[0, "eta"] + pd.Timedelta(minutes=5)
    with pytest.raises(ValueError, match="eta"):
        temporal_split(invalid, at(10), at(12), 60)
    no_eta = labels.drop(columns="eta")
    with pytest.raises(ValueError, match="columns"):
        temporal_split(no_eta, at(10), at(12), 60)
    missing = labels.copy()
    missing.loc[0, "observed_at"] = pd.NaT
    with pytest.raises(ValueError, match="observed_at"):
        temporal_split(missing, at(10), at(12), 60)


def test_rejects_inconsistent_feature_dataset(
    stations: tuple[Station, ...], status: pd.DataFrame, labels: pd.DataFrame
) -> None:
    builder = FeatureBuilder(stations).fit(status, temporal_split(labels, at(10), at(12), 60).train)
    dataset = builder.build(status, labels)
    badly_aligned = FeatureDataset(dataset.frame, dataset.X.iloc[:-1].copy(), dataset.y)
    with pytest.raises(ValueError, match="aligned"):
        temporal_split(badly_aligned, at(10), at(12), 60)
    corrupted_targets = cast(pd.Series, dataset.y.copy())
    corrupted_targets.iloc[0] = 1 - int(corrupted_targets.iloc[0])
    with pytest.raises(ValueError, match="aligned"):
        temporal_split(
            FeatureDataset(dataset.frame, dataset.X, corrupted_targets), at(10), at(12), 60
        )
