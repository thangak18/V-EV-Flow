"""Offline Belib benchmark on the published 15-minute source-clock axis.

This is not a canonical StatusRepository adapter. Unknown ``Other`` remains
separate; naive source timestamps are never asserted to be UTC or +07:00.
"""

from numbers import Integral
from typing import cast

import numpy as np
import pandas as pd

STATES = ("Available", "Charging", "Passive", "Other")
HORIZONS = (15, 30, 60)


def adapt(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Validate observed station aggregates; do not fill missing snapshots."""
    required = ["date", "Station", *STATES]
    if not set(required).issubset(raw.columns) or raw.empty:
        raise ValueError("nonempty source requires date, Station and four state counts")
    frame = raw.loc[:, required].copy()
    if (
        frame.Station.isna().any()
        or not frame.Station.map(lambda value: isinstance(value, str) and bool(value.strip())).all()
    ):
        raise ValueError("Station must contain nonempty identifiers")
    frame["date"] = pd.to_datetime(frame.date, errors="raise")
    if not pd.api.types.is_datetime64_dtype(frame.date.dtype):
        raise ValueError("expected timezone-unspecified source clock; do not convert timestamps")
    if frame.date.isna().any() or not frame.date.eq(frame.date.dt.floor("15min")).all():
        raise ValueError("timestamps must align to the original 15-minute grid")
    if frame.duplicated(["Station", "date"]).any():
        raise ValueError("duplicate station/time observations")
    for column in STATES:
        values = cast(pd.Series, pd.to_numeric(frame[column], errors="raise"))
        if (
            not np.isfinite(values).all()
            or not values.between(0, 3).all()
            or not values.eq(np.floor(values)).all()
        ):
            raise ValueError("state counts must be finite integers between zero and three")
        frame[column] = values.astype("int8")
    if not frame[list(STATES)].sum(axis=1).eq(3).all():
        raise ValueError("published Belib station capacity must equal three")
    frame = frame.sort_values(["Station", "date"]).reset_index(drop=True)
    start, end = frame.date.min(), frame.date.max()
    station_counts = frame.groupby("Station").size()
    slots = int((end - start) / pd.Timedelta(minutes=15)) + 1
    audit = {
        "source_rows": len(frame),
        "station_count": int(frame.Station.nunique()),
        "start": str(start),
        "end": str(end),
        "observed_days": int(frame.date.dt.date.nunique()),
        "source_timezone": "unspecified; source-clock arithmetic only",
        "cadence_minutes": 15,
        "capacity_per_station": 3,
        "missing_station_ticks_global_grid": int(slots * len(station_counts) - len(frame)),
        "per_station_missing_ticks": (slots - station_counts).astype(int).to_dict(),
        "source_columns": list(raw.columns),
        "source_null_counts": raw.isna().sum().to_dict(),
        "duplicate_keys": 0,
        "state_mean_counts": frame[list(STATES)].mean().to_dict(),
        "other_semantics": "reserved/offline/out-of-order, never mapped to broken",
    }
    # Published interval straddles Paris fall-back. Its CSV omits offsets/fold.
    # Conservatively remove that entire day and any ETA/lag needing those rows.
    dst = frame.date.dt.strftime("%Y-%m-%d").isin(["2020-10-25", "2021-03-28"])
    audit["dst_day_rows_excluded"] = int(dst.sum())
    frame = frame.loc[~dst].reset_index(drop=True)
    audit["benchmark_rows"] = len(frame)
    if frame.empty:
        raise ValueError("no unambiguous observations remain")
    return cast(pd.DataFrame, frame), audit


def features(frame: pd.DataFrame) -> pd.DataFrame:
    """Exact backward joins; native missing values need no future-fitted imputer."""
    result = frame[list(STATES)].astype("float32").copy()
    history = frame.set_index(["Station", "date"])[list(STATES)]
    for lag in HORIZONS:
        keys = pd.MultiIndex.from_arrays([frame.Station, frame.date - pd.Timedelta(minutes=lag)])
        values = history.reindex(keys).to_numpy(dtype="float32")
        for i, state in enumerate(STATES):
            result[f"{state}_lag_{lag}"] = values[:, i]
        result[f"lag_{lag}_missing"] = np.isnan(values[:, 0]).astype("float32")
    minute = frame.date.dt.hour * 60 + frame.date.dt.minute
    result["hour_sin"] = np.sin(2 * np.pi * minute / 1440).astype("float32")
    result["hour_cos"] = np.cos(2 * np.pi * minute / 1440).astype("float32")
    result["weekday"] = frame.date.dt.dayofweek.astype("float32")
    return cast(pd.DataFrame, result)


def labels(frame: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Only an exact observed future count is an outcome; never nearest/shift rows."""
    if isinstance(horizon, bool) or not isinstance(horizon, Integral) or horizon not in HORIZONS:
        raise ValueError("benchmark horizons must be 15, 30 or 60 minutes")
    eta = frame.date + pd.Timedelta(minutes=int(horizon))
    lookup = frame.set_index(["Station", "date"]).Available
    keys = pd.MultiIndex.from_arrays([frame.Station, eta])
    future = lookup.reindex(keys).to_numpy(dtype="float32")
    result = pd.DataFrame(
        {
            "observed_at": frame.date,
            "eta": eta,
            "Station": frame.Station,
            "target": (future > 0).astype("int8"),
        }
    )
    return result.loc[np.isfinite(future)]


def partition(
    labels_frame: pd.DataFrame, train_end: pd.Timestamp, calibration_end: pd.Timestamp
) -> dict[str, pd.DataFrame]:
    """Global source-clock cutoffs with a fixed 60-minute observation embargo."""
    if (
        pd.isna(train_end)
        or pd.isna(calibration_end)
        or train_end.tzinfo is not None
        or calibration_end.tzinfo is not None
        or train_end >= calibration_end
    ):
        raise ValueError("ordered source-clock cutoffs without invented timezone required")
    gap = pd.Timedelta(minutes=60)
    t = labels_frame.observed_at
    result = {
        "train": labels_frame.loc[t <= train_end - gap],
        "calibration": labels_frame.loc[(t > train_end) & (t <= calibration_end - gap)],
        "test": labels_frame.loc[t > calibration_end],
    }
    if any(part.empty for part in result.values()):
        raise ValueError("empty chronological partition")
    if (
        result["train"].eta.max() >= result["calibration"].observed_at.min()
        or result["calibration"].eta.max() >= result["test"].observed_at.min()
    ):
        raise ValueError("future-label overlap across partitions")
    return result
