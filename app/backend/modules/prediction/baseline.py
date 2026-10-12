"""Simple observed-time baselines for evaluating ETA availability models.

Persistence reads only current free ports. HourlyRateBaseline learns empirical
availability by *ETA hour* from training labels; unseen hours fall back to the
training-wide rate. Both return a one-dimensional P(available) array.
"""

from typing import cast

import numpy as np
import pandas as pd

from app.backend.modules.prediction.features import FeatureDataset


def _frame(data: pd.DataFrame | FeatureDataset) -> pd.DataFrame:
    if isinstance(data, FeatureDataset):
        return data.frame
    if isinstance(data, pd.DataFrame):
        return data
    raise TypeError("expected a labeled DataFrame or FeatureDataset")


def _eta_hours(frame: pd.DataFrame) -> np.ndarray:
    if "eta" not in frame:
        raise ValueError("missing eta timestamp column")
    eta = cast(pd.Series, frame["eta"])
    if not isinstance(eta.dtype, pd.DatetimeTZDtype):
        raise ValueError("eta must contain timezone-aware timestamps")
    if bool(eta.isna().any()):
        raise ValueError("eta must not have missing timestamps")
    if any(timestamp.utcoffset() != pd.Timedelta(hours=7) for timestamp in eta.array):
        raise ValueError("eta timezone offset must be +07:00")
    return eta.dt.hour.to_numpy(dtype="int64")


class PersistenceBaseline:
    """Binary probability: 1 if a compatible port is free *now*, else 0.

    Input port counts must already represent the requested connector type;
    aggregated counts cannot support mixed-connector stations safely.
    """

    def predict_proba(self, data: pd.DataFrame | FeatureDataset) -> np.ndarray:
        frame = _frame(data)
        if frame.empty:
            raise ValueError("empty input to persistence baseline")
        if "ports_free" not in frame:
            raise ValueError("ports_free is required for persistence")
        try:
            free = cast(pd.Series, frame["ports_free"]).to_numpy(dtype="float64")
        except (TypeError, ValueError) as exc:
            raise ValueError("ports_free must be a nonnegative finite number") from exc
        if not np.isfinite(free).all() or (free < 0).any():
            raise ValueError("ports_free must be nonnegative and finite")
        return (free > 0).astype("float64")


class HourlyRateBaseline:
    """Training-only mean label grouped by known ETA hour (local +07:00)."""

    def __init__(self) -> None:
        self._hourly_rates: dict[int, float] = {}
        self._global_rate: float | None = None

    @property
    def hourly_rates(self) -> dict[int, float]:
        """Independent copy of learned hourly availability frequencies."""
        return self._hourly_rates.copy()

    @property
    def global_rate(self) -> float:
        """Overall training availability frequency used for unseen hours."""
        if self._global_rate is None:
            raise ValueError("fit on the chronological training labels first")
        return self._global_rate

    def fit(self, training: pd.DataFrame | FeatureDataset) -> "HourlyRateBaseline":
        """Learn rates only from the supplied training partition; never refit on test."""
        frame = _frame(training)
        if frame.empty:
            raise ValueError("empty training data for hourly baseline")
        if "target_available" not in frame:
            raise ValueError("target_available is required to fit hourly baseline")
        hours = _eta_hours(frame)
        labels = cast(pd.Series, frame["target_available"])
        if not labels.isin((0, 1)).to_numpy(dtype=bool).all():
            raise ValueError("target_available must be binary")
        if isinstance(training, FeatureDataset) and not training.y.equals(labels):
            raise ValueError("FeatureDataset training y must align with target_available")

        targets = labels.to_numpy(dtype="float64")
        # Build from positions rather than pandas index alignment: callers may
        # pass shuffled training labels with non-consecutive original indices.
        counts = np.bincount(hours, minlength=24)
        positives = np.bincount(hours, weights=targets, minlength=24)
        learned = {
            hour: float(positives[hour] / counts[hour]) for hour in range(24) if counts[hour] > 0
        }
        self._hourly_rates = learned
        self._global_rate = float(targets.mean())
        return self

    def predict_proba(self, data: pd.DataFrame | FeatureDataset) -> np.ndarray:
        if self._global_rate is None:
            raise ValueError("fit on the chronological training labels before predict")
        frame = _frame(data)
        if frame.empty:
            raise ValueError("empty input to hourly baseline")
        hours = _eta_hours(frame)
        return np.array(
            [self._hourly_rates.get(int(hour), self._global_rate) for hour in hours],
            dtype="float64",
        )
