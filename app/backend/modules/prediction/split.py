"""Chronological train/calibration/test splitting with a future-label embargo.

Split labeled rows *before* fitting preprocessing or model parameters. Cutoffs
apply globally across every station and scenario. Each boundary removes all
observations in its preceding maximum-horizon window, including the cutoff
itself, so training labels cannot observe evaluation-period feature times.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Generic, TypeVar, cast, overload

import numpy as np
import pandas as pd

from app.backend.modules.prediction.features import FeatureDataset
from app.backend.modules.prediction.labels import LABEL_COLUMNS

_LABEL_KEYS = ("scenario", "station_id", "observed_at", "horizon_minutes")
_SORT_KEYS = ("observed_at", "scenario", "station_id", "horizon_minutes")
_OFFSET = timedelta(hours=7)
_PARTITIONS = ("train", "calibration", "test")
Partition = TypeVar("Partition", pd.DataFrame, FeatureDataset)


@dataclass(frozen=True)
class SplitMetadata:
    """Boundaries, retained sample counts/time ranges, and embargo removals."""

    train_end: pd.Timestamp
    calibration_end: pd.Timestamp
    max_horizon_minutes: int
    counts: dict[str, int]
    observed_ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]]
    dropped_for_embargo: dict[str, int]


@dataclass(frozen=True)
class DatasetSplit(Generic[Partition]):
    """Nonempty chronological partitions plus reproducible split metadata."""

    train: Partition
    calibration: Partition
    test: Partition
    metadata: SplitMetadata


def _cutoff(value: object, name: str) -> pd.Timestamp:
    if not isinstance(value, (pd.Timestamp, datetime, str)):
        raise ValueError(f"{name} must be a timezone-aware timestamp")
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a valid timezone-aware timestamp") from exc
    if not isinstance(timestamp, pd.Timestamp) or timestamp.tzinfo is None:
        raise ValueError(f"{name} must have a timezone offset (+07:00)")
    if timestamp.utcoffset() != _OFFSET:
        raise ValueError(f"{name} must use timezone offset +07:00")
    return timestamp


def _validate_frame(frame: pd.DataFrame, max_horizon_minutes: int) -> None:
    if frame.empty:
        raise ValueError("empty labels; cannot split")
    missing = set(LABEL_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"missing required label columns: {sorted(missing)}")
    if frame.duplicated(subset=list(_LABEL_KEYS)).any():
        raise ValueError("duplicate labels by scenario/station/observed_at/horizon")

    for column in ("observed_at", "eta"):
        if not isinstance(frame[column].dtype, pd.DatetimeTZDtype):
            raise ValueError(f"{column} must have timezone-aware timestamps")
        if bool(frame[column].isna().any()):
            raise ValueError(f"{column} has missing timestamps")
        # The canonical simulator and label builder operate in +07:00.
        if any(value.utcoffset() != _OFFSET for value in frame[column].array):
            raise ValueError(f"{column} must use the +07:00 timezone offset")

    horizons = cast(pd.Series, frame["horizon_minutes"])
    if (
        not pd.api.types.is_integer_dtype(horizons.dtype)
        or bool(horizons.isna().any())
        or not (horizons > 0).to_numpy(dtype=bool).all()
        or not (horizons.to_numpy(dtype="int64") % 5 == 0).all()
        or bool((horizons > max_horizon_minutes).any())
    ):
        raise ValueError("label horizon must be positive, divisible by five, and <= max horizon")

    expected_eta = frame["observed_at"] + pd.to_timedelta(horizons, unit="m")
    if not (frame["eta"] == expected_eta).to_numpy(dtype=bool).all():
        raise ValueError("eta must equal observed_at plus horizon_minutes")
    targets = cast(pd.Series, frame["target_available"])
    if not targets.isin((0, 1)).to_numpy(dtype=bool).all():
        raise ValueError("target_available must be binary")


def _validate_features(dataset: FeatureDataset) -> None:
    frame, x, y = dataset.frame, dataset.X, dataset.y
    if (
        not isinstance(frame, pd.DataFrame)
        or not isinstance(x, pd.DataFrame)
        or not isinstance(y, pd.Series)
        or len(frame) != len(x)
        or len(frame) != len(y)
        or not frame.index.equals(x.index)
        or not frame.index.equals(y.index)
        or not x.columns.is_unique
        or not x.columns.isin(frame.columns).all()
        or not x.equals(frame.loc[:, list(x.columns)])
        or "target_available" not in frame
        or not y.equals(frame["target_available"])
    ):
        raise ValueError("FeatureDataset frame, X and y must be aligned")


@overload
def temporal_split(
    dataset: pd.DataFrame,
    train_end: object,
    calibration_end: object,
    max_horizon_minutes: object,
) -> DatasetSplit[pd.DataFrame]: ...


@overload
def temporal_split(
    dataset: FeatureDataset,
    train_end: object,
    calibration_end: object,
    max_horizon_minutes: object,
) -> DatasetSplit[FeatureDataset]: ...


def temporal_split(
    dataset: pd.DataFrame | FeatureDataset,
    train_end: object,
    calibration_end: object,
    max_horizon_minutes: object,
) -> DatasetSplit[pd.DataFrame] | DatasetSplit[FeatureDataset]:
    """Split by shared clock boundaries and embargo every preceding horizon.

    ``train`` contains times <= ``train_end - gap``. ``calibration`` contains
    times > ``train_end`` and <= ``calibration_end - gap``. ``test`` contains
    times > ``calibration_end``. Rows in (boundary - gap, boundary] are dropped
    for *all* horizons, including short ones. ``gap`` is the supplied maximum
    prediction horizon and must cover all labels in the dataset.

    Input can be a label DataFrame or aligned ``FeatureDataset``. All outputs
    are sorted chronologically and indexed from zero; inputs remain unchanged.
    FeatureBuilder.fit must receive only ``split.train`` labels, never the full
    data or the calibration/test partitions.
    """
    if isinstance(max_horizon_minutes, (bool, np.bool_)) or not isinstance(
        max_horizon_minutes, (int, np.integer)
    ):
        raise ValueError("max horizon must be an integer number of minutes")
    gap = int(max_horizon_minutes)
    if gap <= 0 or gap % 5:
        raise ValueError("max horizon must be positive and divisible by five")

    train_cutoff = _cutoff(train_end, "train_end")
    calibration_cutoff = _cutoff(calibration_end, "calibration_end")
    if train_cutoff >= calibration_cutoff:
        raise ValueError("train_end must be before calibration_end")

    if isinstance(dataset, FeatureDataset):
        _validate_features(dataset)
        frame = dataset.frame
    elif isinstance(dataset, pd.DataFrame):
        frame = dataset
    else:
        raise TypeError("dataset must be a label DataFrame or FeatureDataset")
    _validate_frame(frame, gap)

    # Sort by *global* observed time. Original indices may be shuffled or
    # duplicated, so first map ordering to row positions and use iloc.
    order = (
        frame.reset_index(drop=True)
        .sort_values(list(_SORT_KEYS), kind="mergesort")
        .index.to_numpy(dtype="int64")
    )
    sorted_frame = frame.iloc[order].reset_index(drop=True)
    observed = cast(pd.Series, sorted_frame["observed_at"])
    embargo = pd.Timedelta(minutes=gap)
    train_mask = observed <= train_cutoff - embargo
    calibration_mask = (observed > train_cutoff) & (observed <= calibration_cutoff - embargo)
    test_mask = observed > calibration_cutoff

    masks = {"train": train_mask, "calibration": calibration_mask, "test": test_mask}
    if any(not bool(mask.any()) for mask in masks.values()):
        raise ValueError("empty train/calibration/test partition after temporal embargo")

    # These rows are deliberately unavailable to training/calibration; count
    # cutoffs with the preceding embargo so every input row is accounted for.
    dropped = {
        "train": int(((observed > train_cutoff - embargo) & (observed <= train_cutoff)).sum()),
        "calibration": int(
            ((observed > calibration_cutoff - embargo) & (observed <= calibration_cutoff)).sum()
        ),
    }
    counts = {name: int(mask.sum()) for name, mask in masks.items()}
    if sum(counts.values()) + sum(dropped.values()) != len(frame):
        raise ValueError("calibration window is too short for the temporal embargo")

    ranges = {
        name: (cast(pd.Timestamp, observed[mask].min()), cast(pd.Timestamp, observed[mask].max()))
        for name, mask in masks.items()
    }
    if not (
        sorted_frame.loc[train_mask, "eta"].max() < ranges["calibration"][0]
        and sorted_frame.loc[calibration_mask, "eta"].max() < ranges["test"][0]
    ):
        raise ValueError("future label leakage across temporal partitions")

    metadata = SplitMetadata(
        train_end=train_cutoff,
        calibration_end=calibration_cutoff,
        max_horizon_minutes=gap,
        counts=counts,
        observed_ranges=ranges,
        dropped_for_embargo=dropped,
    )
    if isinstance(dataset, FeatureDataset):
        x = dataset.X.iloc[order].reset_index(drop=True)
        y = dataset.y.iloc[order].reset_index(drop=True)

        def subset(name: str) -> FeatureDataset:
            mask = masks[name]
            return FeatureDataset(
                frame=sorted_frame.loc[mask].reset_index(drop=True),
                X=x.loc[mask].reset_index(drop=True),
                y=y.loc[mask].reset_index(drop=True),
            )

        return DatasetSplit(subset("train"), subset("calibration"), subset("test"), metadata)

    return DatasetSplit(
        *(sorted_frame.loc[masks[name]].reset_index(drop=True) for name in _PARTITIONS),
        metadata=metadata,
    )
