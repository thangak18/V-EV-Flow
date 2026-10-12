"""Deterministic, observed-at-only features for availability prediction.

Inputs must already have passed ``validate_status_frame``. Fit the missing-lag
imputation on the chronological *training* labels only, then reuse that builder
for calibration, test, and inference. No outcome at ETA enters ``X``.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd

from app.backend.contracts.enums import Scenario
from app.backend.contracts.stations import Station
from app.backend.modules.prediction.dataset import COUNT_COLUMNS, KEY_COLUMNS, STATUS_COLUMNS
from app.backend.modules.prediction.labels import LABEL_COLUMNS

LAG_MINUTES = (15, 30, 60)
LAG_COLUMNS = tuple(f"{count}_lag_{minutes}" for minutes in LAG_MINUTES for count in COUNT_COLUMNS)
FEATURE_COLUMNS = (
    *COUNT_COLUMNS,
    *LAG_COLUMNS,
    "lag_15_missing",
    "lag_30_missing",
    "lag_60_missing",
    "hour_sin",
    "hour_cos",
    "weekday",
    "is_weekend",
    "is_holiday_scenario",
    "scenario_normal",
    "scenario_holiday_30_4",
    "scenario_tet",
    "n_ports",
    "power_kw",
    "station_type_urban",
    "station_type_highway",
    "station_type_other",
    "horizon_minutes",
)
_LABEL_KEYS = ("scenario", "station_id", "observed_at", "horizon_minutes")
_SCENARIOS = frozenset(item.value for item in Scenario)


@dataclass(frozen=True)
class FeatureDataset:
    """Aligned labeled rows, ordered numeric model inputs, and binary labels."""

    frame: pd.DataFrame
    X: pd.DataFrame
    y: pd.Series


class FeatureBuilder:
    """Produce fixed-schema features, with training-only lag imputation."""

    def __init__(self, stations: Sequence[Station]) -> None:
        metadata = [
            {
                "station_id": station.station_id,
                "n_ports": station.n_ports,
                "power_kw": station.power_kw,
                "station_type": station.station_type.lower(),
            }
            for station in stations
        ]
        if not metadata:
            raise ValueError("station metadata is empty")
        if len({row["station_id"] for row in metadata}) != len(metadata):
            raise ValueError("duplicate station_id in station metadata")
        self._metadata = pd.DataFrame(metadata)
        self._lag_fill_values: dict[str, float] = {}
        self._fitted = False

    @property
    def lag_fill_values(self) -> dict[str, float]:
        """A copy of the training medians, keyed by lag feature name."""
        return self._lag_fill_values.copy()

    def fit(self, status_frame: pd.DataFrame, training_labels: pd.DataFrame) -> "FeatureBuilder":
        """Learn lag medians exclusively from labeled training observations."""
        if not isinstance(training_labels, pd.DataFrame):
            raise TypeError("training labels must be a DataFrame")
        if training_labels.empty:
            raise ValueError("empty training labels; cannot fit feature imputation")
        training = self._raw_features(status_frame, training_labels)
        values: dict[str, float] = {}
        for column in LAG_COLUMNS:
            observed = cast(pd.Series, training[column]).dropna().to_numpy(dtype=float)
            values[column] = float(np.median(observed)) if len(observed) else 0.0
        self._lag_fill_values = values
        self._fitted = True
        return self

    def build(self, status_frame: pd.DataFrame, labels: pd.DataFrame) -> FeatureDataset:
        """Transform labeled observations without updating training medians."""
        if not self._fitted:
            raise ValueError("fit the FeatureBuilder on training labels before build")
        result = self._raw_features(status_frame, labels)
        for column, median in self._lag_fill_values.items():
            result[column] = result[column].fillna(median).astype("float64")

        columns = [column for column in LABEL_COLUMNS if column not in FEATURE_COLUMNS]
        result = result.loc[:, [*columns, *FEATURE_COLUMNS]].reset_index(drop=True)
        X = result.loc[:, list(FEATURE_COLUMNS)].copy()
        if bool(X.isna().any().any()):
            raise ValueError("unexpected missing model feature after lag imputation")
        return FeatureDataset(frame=result, X=X, y=result["target_available"].copy())

    def _raw_features(self, status_frame: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(status_frame, pd.DataFrame):
            raise TypeError("station_status must be a DataFrame")
        if set(status_frame.columns) != set(STATUS_COLUMNS):
            raise ValueError(f"station_status columns must be exactly {list(STATUS_COLUMNS)}")
        if not isinstance(status_frame["ts"].dtype, pd.DatetimeTZDtype):
            raise ValueError("station_status ts must be timezone-aware")
        if status_frame.duplicated(subset=list(KEY_COLUMNS)).any():
            raise ValueError("duplicate scenario/station/timestamp in station_status")
        if not isinstance(labels, pd.DataFrame):
            raise TypeError("labels must be a DataFrame")
        if set(labels.columns) != set(LABEL_COLUMNS):
            raise ValueError(f"labels columns must be exactly {list(LABEL_COLUMNS)}")
        if labels.empty:
            raise ValueError("labels are empty")
        if labels.duplicated(subset=list(_LABEL_KEYS)).any():
            raise ValueError("duplicate scenario/station/observed_at/horizon label keys")
        for column in ("observed_at", "eta"):
            if not isinstance(labels[column].dtype, pd.DatetimeTZDtype):
                raise ValueError(f"{column} must contain timezone-aware timestamps")
        scenarios = cast(pd.Series, labels["scenario"])
        if not scenarios.isin(tuple(_SCENARIOS)).to_numpy(dtype=bool).all():
            raise ValueError("unrecognized scenario in labels")
        horizons = cast(pd.Series, labels["horizon_minutes"])
        if (
            not pd.api.types.is_integer_dtype(horizons.dtype)
            or not (horizons > 0).to_numpy(dtype=bool).all()
            or not np.equal(horizons.to_numpy(dtype="int64") % 5, 0).all()
        ):
            raise ValueError("horizon_minutes must be positive integer multiples of 5")
        eta = cast(pd.Series, labels["eta"])
        observed_at = cast(pd.Series, labels["observed_at"])
        expected_eta = observed_at + pd.to_timedelta(horizons.to_numpy(dtype="int64"), unit="m")
        if not (eta == expected_eta).to_numpy(dtype=bool).all():
            raise ValueError("eta must equal observed_at plus horizon_minutes")
        target = cast(pd.Series, labels["target_available"])
        if not target.isin((0, 1)).to_numpy(dtype=bool).all():
            raise ValueError("target_available must be binary")

        ordered = (
            labels.loc[:, list(LABEL_COLUMNS)]
            .sort_values(list(_LABEL_KEYS), kind="mergesort")
            .reset_index(drop=True)
        )
        # Join each snapshot by its exact observed_at, never by nearest time.
        snapshots = status_frame.loc[:, list(STATUS_COLUMNS)].copy()
        current = snapshots.rename(columns={"ts": "observed_at"})
        result = ordered.merge(
            current,
            on=["scenario", "station_id", "observed_at"],
            how="left",
            validate="many_to_one",
            indicator=True,
            sort=False,
        )
        if not (result["_merge"] == "both").all():
            raise ValueError(
                "labels contain a station/observed_at with no matching status snapshot"
            )
        result = result.drop(columns="_merge")

        # Positional shift is unsafe if a five-minute bucket is missing.
        for minutes in LAG_MINUTES:
            join_time = "_lag_time"
            result[join_time] = result["observed_at"] - pd.Timedelta(minutes=minutes)
            lag_names = {count: f"{count}_lag_{minutes}" for count in COUNT_COLUMNS}
            past = snapshots.rename(columns={"ts": join_time, **lag_names})
            result = result.merge(
                past.loc[:, ["scenario", "station_id", join_time, *lag_names.values()]],
                on=["scenario", "station_id", join_time],
                how="left",
                validate="many_to_one",
                sort=False,
            ).drop(columns=join_time)
            # All counts are present together in a valid snapshot, even if zero.
            result[f"lag_{minutes}_missing"] = (
                result[f"ports_free_lag_{minutes}"].isna().astype("int8")
            )

        result = result.merge(self._metadata, on="station_id", how="left", validate="many_to_one")
        if result["n_ports"].isna().any():
            raise ValueError("station in labels is absent from station metadata")

        observed = result["observed_at"].dt
        fractional_hour = observed.hour + observed.minute / 60
        angle = 2 * np.pi * fractional_hour / 24
        result["hour_sin"] = np.sin(angle)
        result["hour_cos"] = np.cos(angle)
        result["weekday"] = observed.dayofweek.astype("int8")
        result["is_weekend"] = (result["weekday"] >= 5).astype("int8")
        result["is_holiday_scenario"] = (result["scenario"] != Scenario.NORMAL.value).astype("int8")
        for scenario in Scenario:
            result[f"scenario_{scenario.value}"] = (result["scenario"] == scenario.value).astype(
                "int8"
            )
        for station_type in ("urban", "highway"):
            result[f"station_type_{station_type}"] = (
                result["station_type"] == station_type
            ).astype("int8")
        result["station_type_other"] = (~result["station_type"].isin(("urban", "highway"))).astype(
            "int8"
        )
        return result
