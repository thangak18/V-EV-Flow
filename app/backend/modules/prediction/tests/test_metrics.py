"""Probability evaluation and training-only baseline regression tests."""

from typing import cast

import numpy as np
import pandas as pd
import pytest

from app.backend.modules.prediction.baseline import HourlyRateBaseline, PersistenceBaseline
from app.backend.modules.prediction.features import FeatureDataset
from app.backend.modules.prediction.metrics import evaluate_probabilities


def rows(hours: tuple[str, ...], targets: tuple[int, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "station_id": ["S001"] * len(hours),
            "scenario": ["normal"] * len(hours),
            "observed_at": pd.to_datetime([f"2026-10-13T{hour}:00+07:00" for hour in hours])
            - pd.Timedelta(minutes=30),
            "eta": pd.to_datetime([f"2026-10-13T{hour}:00+07:00" for hour in hours]),
            "horizon_minutes": [30] * len(hours),
            "ports_free": [0, 2, 0, 1][: len(hours)],
            "target_available": targets,
        }
    )


def test_brier_auc_counts_and_expected_calibration_error() -> None:
    result = evaluate_probabilities([0, 1, 1, 0], [0.25, 0.75, 0.75, 0.25], n_bins=2)
    assert result.sample_count == 4
    assert result.positive_count == 2
    assert result.positive_rate == pytest.approx(0.5)
    assert result.brier_score == pytest.approx(0.0625)
    assert result.auc == pytest.approx(1.0)
    assert result.ece == pytest.approx(0.25)
    assert [(b.count, b.mean_predicted, b.observed_rate) for b in result.calibration] == [
        (2, 0.25, 0.0),
        (2, 0.75, 1.0),
    ]


def test_one_class_auc_is_none_and_empty_bins_are_explicit() -> None:
    result = evaluate_probabilities(np.ones(4), np.full(4, 0.8), n_bins=5)
    assert result.auc is None
    assert result.sample_count == 4
    assert result.brier_score == pytest.approx(0.04)
    assert sum(bin_.count for bin_ in result.calibration) == 4
    assert sum(bin_.count == 0 for bin_ in result.calibration) == 4
    assert all(
        bin_.mean_predicted is None and bin_.observed_rate is None
        for bin_ in result.calibration
        if bin_.count == 0
    )


def test_calibration_boundaries_cover_zero_and_one() -> None:
    result = evaluate_probabilities([0, 1, 1, 0], [0.0, 0.5, 1.0, 0.499], n_bins=2)
    assert tuple(bin_.count for bin_ in result.calibration) == (2, 2)
    assert result.calibration[0].lower_bound == 0.0
    assert result.calibration[0].upper_bound == 0.5
    assert result.calibration[1].lower_bound == 0.5
    assert result.calibration[1].upper_bound == 1.0
    assert result.calibration[1].observed_rate == pytest.approx(1.0)


@pytest.mark.parametrize(
    "truth,prediction,warning",
    [
        ([], [], "empty"),
        ([0, 1], [0.5], "length"),
        ([0, 2], [0.5, 0.5], "binary"),
        ([0, np.nan], [0.5, 0.5], "binary"),
        ([0, 1], [np.nan, 0.5], "finite"),
        ([0, 1], [np.inf, 0.5], "finite"),
        ([0, 1], [0.5, -0.1], "range"),
        ([0, 1], [0.5, 1.1], "range"),
        ([[0, 1]], [0.1, 0.9], "one-dimensional"),
        ([0, 1], [[0.1, 0.9]], "one-dimensional"),
    ],
)
def test_metrics_reject_invalid_arrays(truth: object, prediction: object, warning: str) -> None:
    with pytest.raises(ValueError, match=warning):
        evaluate_probabilities(truth, prediction)


@pytest.mark.parametrize("bins", [0, -1, 1.5, True])
def test_metrics_reject_invalid_bin_count(bins: object) -> None:
    with pytest.raises(ValueError, match="n_bins"):
        evaluate_probabilities([0, 1], [0.2, 0.8], n_bins=bins)


def test_metrics_are_deterministic_and_do_not_change_inputs() -> None:
    truth = np.array([0, 1, 0, 1, 1], dtype=np.int8)
    prediction = np.array([0.1, 0.5, 0.2, 1.0, 0.8])
    before_truth, before_prediction = truth.copy(), prediction.copy()
    first = evaluate_probabilities(truth, prediction)
    assert first == evaluate_probabilities(truth[::-1], prediction[::-1])
    np.testing.assert_array_equal(truth, before_truth)
    np.testing.assert_array_equal(prediction, before_prediction)


def test_persistence_uses_only_observed_free_ports() -> None:
    frame = rows(("08:05", "08:10", "08:15", "08:20"), (1, 0, 1, 0))
    baseline = PersistenceBaseline()
    before = frame.copy(deep=True)
    prediction = baseline.predict_proba(frame)
    np.testing.assert_array_equal(prediction, [0.0, 1.0, 0.0, 1.0])
    future_modified = frame.copy(deep=True)
    future_modified["target_available"] = 1 - future_modified["target_available"]
    future_modified["eta"] += pd.Timedelta(hours=5)
    np.testing.assert_array_equal(prediction, baseline.predict_proba(future_modified))
    pd.testing.assert_frame_equal(before, frame)


def test_persistence_supports_feature_dataset() -> None:
    frame = rows(("08:05", "08:10"), (1, 0))
    dataset = FeatureDataset(
        frame,
        frame.loc[:, ["ports_free"]].copy(),
        cast(pd.Series, frame["target_available"]),
    )
    np.testing.assert_array_equal(PersistenceBaseline().predict_proba(dataset), [0.0, 1.0])


@pytest.mark.parametrize("free", [-1, np.nan, np.inf])
def test_persistence_rejects_invalid_free_ports(free: float) -> None:
    frame = rows(("08:05",), (0,))
    frame["ports_free"] = free
    with pytest.raises(ValueError, match="ports_free"):
        PersistenceBaseline().predict_proba(frame)


def test_persistence_rejects_missing_or_empty_input() -> None:
    frame = rows(("08:05",), (0,))
    with pytest.raises(ValueError, match="ports_free"):
        PersistenceBaseline().predict_proba(frame.drop(columns="ports_free"))
    with pytest.raises(ValueError, match="empty"):
        PersistenceBaseline().predict_proba(frame.iloc[:0])


def test_hourly_baseline_fits_only_provided_training_rows_with_global_fallback() -> None:
    training = rows(("08:05", "08:10", "09:05", "09:10"), (1, 0, 1, 1))
    observed = rows(("08:55", "09:55", "10:05"), (0, 0, 0))
    model = HourlyRateBaseline().fit(training)
    assert model.global_rate == pytest.approx(0.75)
    assert model.hourly_rates == {8: 0.5, 9: 1.0}
    np.testing.assert_allclose(model.predict_proba(observed), [0.5, 1.0, 0.75])
    # Evaluation outcome labels must never be read when computing predictions.
    modified = observed.copy()
    modified["target_available"] = 1
    np.testing.assert_allclose(model.predict_proba(modified), [0.5, 1.0, 0.75])
    assert model.hourly_rates == {8: 0.5, 9: 1.0}


def test_hourly_baseline_uses_eta_hour_and_handles_midnight() -> None:
    training = rows(("08:05", "09:05"), (1, 0))
    model = HourlyRateBaseline().fit(training)
    evaluation = rows(("08:05", "09:05", "10:05"), (0, 0, 1))
    evaluation["observed_at"] -= pd.Timedelta(hours=7)
    np.testing.assert_allclose(model.predict_proba(evaluation), [1.0, 0.0, 0.5])


def test_hourly_baseline_accepts_feature_dataset_and_is_order_independent() -> None:
    training = rows(("08:05", "08:10", "09:05", "09:10"), (1, 0, 0, 1))
    before = training.copy(deep=True)
    features = FeatureDataset(
        training,
        training.loc[:, ["ports_free"]].copy(),
        cast(pd.Series, training["target_available"]).copy(),
    )
    model = HourlyRateBaseline().fit(features)
    other = HourlyRateBaseline().fit(training.sample(frac=1, random_state=42))
    assert model.hourly_rates == other.hourly_rates
    np.testing.assert_allclose(model.predict_proba(features), other.predict_proba(training))
    pd.testing.assert_frame_equal(before, training)


def test_hourly_baseline_requires_fit_and_valid_training_labels() -> None:
    frame = rows(("08:05", "08:10"), (1, 0))
    with pytest.raises(ValueError, match="fit|training"):
        HourlyRateBaseline().predict_proba(frame)
    with pytest.raises(ValueError, match="empty"):
        HourlyRateBaseline().fit(frame.iloc[:0])
    with pytest.raises(ValueError, match="target_available"):
        HourlyRateBaseline().fit(frame.drop(columns="target_available"))
    invalid = frame.copy()
    invalid.loc[0, "target_available"] = 2
    with pytest.raises(ValueError, match="binary"):
        HourlyRateBaseline().fit(invalid)


def test_hourly_baseline_rejects_missing_or_naive_eta() -> None:
    frame = rows(("08:05", "08:10"), (1, 0))
    model = HourlyRateBaseline().fit(frame)
    with pytest.raises(ValueError, match="eta"):
        model.predict_proba(frame.drop(columns="eta"))
    naive = frame.copy()
    naive["eta"] = naive["eta"].dt.tz_localize(None)
    with pytest.raises(ValueError, match="timezone"):
        model.predict_proba(naive)
    missing = frame.copy()
    missing.loc[0, "eta"] = pd.NaT
    with pytest.raises(ValueError, match="eta"):
        model.predict_proba(missing)
