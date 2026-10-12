"""Build training labels for port availability at an exact future ETA.

Call ``validate_status_frame`` before this function. Station-level port counts
are suitable for a single compatible connector type; aggregate counts cannot
determine connector-specific availability at a mixed-connector station.
"""

from collections.abc import Sequence
from datetime import timedelta

import numpy as np
import pandas as pd

from app.backend.modules.prediction.dataset import KEY_COLUMNS, STATUS_COLUMNS

LABEL_COLUMNS = (
    "station_id",
    "scenario",
    "observed_at",
    "eta",
    "horizon_minutes",
    "target_available",
)
_CANONICAL_OFFSET = timedelta(hours=7)
_INTERVAL_MINUTES = 5


def _check_horizons(horizons_minutes: Sequence[int]) -> list[int]:
    if not horizons_minutes:
        raise ValueError("at least one horizon is required")

    validated: list[int] = []
    for value in horizons_minutes:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
            raise ValueError("horizon must be an integer number of minutes")
        horizon = int(value)
        if horizon <= 0 or horizon % _INTERVAL_MINUTES != 0:
            raise ValueError("horizon must be positive and divisible by 5 minutes")
        validated.append(horizon)

    if len(validated) != len(set(validated)):
        raise ValueError("duplicate horizon values")
    return sorted(validated)


def build_labels(frame: pd.DataFrame, horizons_minutes: Sequence[int]) -> pd.DataFrame:
    """Create ``target_available = int(ports_free at t + h > 0)``.

    Each label uses only a future snapshot with the *same* scenario/station
    and an exact timestamp equal to ``observed_at + horizon``. Rows without
    that future snapshot are omitted. In particular, missing intermediate
    five-minute records do not shift the target onto a different ETA.

    The input is the canonical frame returned by ``validate_status_frame``;
    features must separately use only data at or before ``observed_at``.
    The original DataFrame is left unchanged.
    """
    horizons = _check_horizons(horizons_minutes)
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("station_status must be a DataFrame")
    if len(frame.columns) != len(STATUS_COLUMNS) or set(frame.columns) != set(STATUS_COLUMNS):
        raise ValueError(f"station_status columns must be exactly {list(STATUS_COLUMNS)}")
    if not isinstance(frame["ts"].dtype, pd.DatetimeTZDtype) or bool(frame["ts"].isna().any()):
        raise ValueError("ts must contain validated timezone-aware timestamps")
    if not frame.empty and any(
        timestamp.utcoffset() != _CANONICAL_OFFSET for timestamp in frame["ts"]
    ):
        raise ValueError("ts must use the +07:00 timezone offset")
    if frame.duplicated(subset=list(KEY_COLUMNS)).any():
        raise ValueError("station_status keys (scenario, station_id, ts) must be unique")

    observations = frame.loc[:, ["scenario", "station_id", "ts"]].rename(
        columns={"ts": "observed_at"}
    )
    available_at_eta = frame.loc[:, ["scenario", "station_id", "ts", "ports_free"]].rename(
        columns={"ts": "eta", "ports_free": "future_ports_free"}
    )

    batches: list[pd.DataFrame] = []
    for horizon in horizons:
        requested = observations.copy()
        requested["eta"] = requested["observed_at"] + pd.Timedelta(minutes=horizon)
        matched = requested.merge(
            available_at_eta,
            on=["scenario", "station_id", "eta"],
            how="inner",
            validate="many_to_one",
            sort=False,
        )
        matched["horizon_minutes"] = horizon
        matched["target_available"] = (matched["future_ports_free"] > 0).astype("int8")
        batches.append(matched.loc[:, list(LABEL_COLUMNS)])

    return (
        pd.concat(batches, ignore_index=True)
        .sort_values(["scenario", "station_id", "observed_at", "horizon_minutes"], kind="mergesort")
        .reset_index(drop=True)
    )
