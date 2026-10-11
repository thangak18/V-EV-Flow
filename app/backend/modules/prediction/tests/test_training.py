"""End-to-end synthetic checks for the train/calibrate/evaluate boundary."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from app.backend.contracts.stations import Station
from app.backend.modules.prediction.dataset import validate_status_frame
from app.backend.modules.prediction.features import FEATURE_COLUMNS
from app.backend.modules.prediction.labels import build_labels
from app.backend.modules.prediction.split import temporal_split
from app.backend.modules.prediction.training import (
    TrainingConfig,
    evaluate_holdout,
    train_candidate,
)


@pytest.fixture(scope="module")
def stations() -> tuple[Station, ...]:
    return tuple(
        Station.model_validate(
            {
                "station_id": f"S00{index}",
                "name": f"Synthetic station {index}",
                "lat": 10.0 + index / 10,
                "lng": 107.0,
                "n_ports": capacity,
                "power_kw": 120.0,
                "connector_types": ["CCS2"],
                "network": "synthetic",
                "station_type": "highway",
                "source": "simulated test generator",
                "assumptions": ["one connector type"],
            }
        )
        for index, capacity in ((1, 6), (2, 8))
    )


def synthetic_status(
    stations: tuple[Station, ...],
    *,
    seed: int,
    start: str,
    steps: int = 420,
    holiday_peak: float = 0.1,
    outage_probability: float = 0.02,
) -> pd.DataFrame:
    """Five-minute mock traffic with explicit knobs for an out-of-distribution holdout."""
    rng = np.random.default_rng(seed)
    beginning = pd.Timestamp(start)
    records = []
    for scenario in ("normal", "tet"):
        for station in stations:
            for tick in range(steps):
                clock = beginning + pd.Timedelta(minutes=tick * 5)
                rush = 0.22 if 15 <= clock.hour <= 22 else 0.03
                scenario_pressure = holiday_peak if scenario == "tet" else 0.0
                broken = int(rng.binomial(station.n_ports, outage_probability))
                working = station.n_ports - broken
                free_share = np.clip(0.68 - rush - scenario_pressure, 0.04, 0.95)
                free = int(rng.binomial(working, free_share))
                records.append(
                    {
                        "station_id": station.station_id,
                        "scenario": scenario,
                        "ts": clock,
                        "ports_free": free,
                        "ports_busy": working - free,
                        "ports_broken": broken,
                    }
                )
    return validate_status_frame(pd.DataFrame(records), stations)


@pytest.fixture(scope="module")
def setup_training(stations: tuple[Station, ...]):  # noqa: ANN201
    status = synthetic_status(stations, seed=42, start="2026-10-12T00:00:00+07:00")
    labels = build_labels(status, [15, 30])
    split = temporal_split(
        labels,
        train_end="2026-10-12T09:00:00+07:00",
        calibration_end="2026-10-12T19:00:00+07:00",
        max_horizon_minutes=30,
    )
    return status, split


@pytest.fixture(scope="module")
def trained(stations: tuple[Station, ...], setup_training):  # noqa: ANN201
    status, split = setup_training
    config = TrainingConfig(random_state=42, n_estimators=30, min_child_samples=4)
    return train_candidate(split, config, status_frame=status, stations=stations, seed=42)


def test_trains_lightgbm_and_compares_all_models(trained, setup_training) -> None:  # noqa: ANN001
    _, split = setup_training
    assert trained.model.__class__.__name__ == "LGBMClassifier"
    assert trained.calibration_method in ("isotonic", "platt")
    assert set(trained.calibration_brier) == {"isotonic", "platt"}
    assert trained.calibration_brier[trained.calibration_method] == pytest.approx(
        min(trained.calibration_brier.values())
    )
    assert set(trained.test_metrics) == {
        "lightgbm_raw",
        "lightgbm_calibrated",
        "persistence",
        "hourly_rate",
    }
    assert all(
        m.sample_count == len(split.test) and 0 <= m.brier_score <= 1
        for m in trained.test_metrics.values()
    )
    assert trained.split_metadata == split.metadata
    assert trained.sample_counts == split.metadata.counts
    assert trained.scenarios == ("normal", "tet")
    assert trained.seed == 42
    assert trained.data_type == "simulated"
    assert trained.feature_columns == FEATURE_COLUMNS
    assert len(trained.feature_builder.lag_fill_values) == 9
    assert trained.test_metrics["lightgbm_raw"].sample_count > 0
    assert trained.test_metrics["lightgbm_calibrated"].ece >= 0
    assert (
        trained.test_metrics["hourly_rate"].auc is None
        or 0 <= trained.test_metrics["hourly_rate"].auc <= 1
    )


def test_predictions_are_bounded_and_repeatable(trained, setup_training, stations) -> None:  # noqa: ANN001
    status, split = setup_training
    test_features = trained.feature_builder.build(status, split.test)
    probabilities = trained.predict_proba(test_features.X)
    assert probabilities.shape == (len(split.test), 2)
    assert np.isfinite(probabilities).all()
    assert (probabilities >= 0).all() and (probabilities <= 1).all()
    np.testing.assert_allclose(probabilities.sum(axis=1), 1)
    repeat = train_candidate(split, trained.config, status_frame=status, stations=stations, seed=42)
    np.testing.assert_allclose(probabilities, repeat.predict_proba(test_features.X))
    assert trained.test_metrics == repeat.test_metrics


def test_calibration_and_test_labels_never_fit_the_raw_model(
    trained, setup_training, stations
) -> None:  # noqa: ANN001
    status, split = setup_training
    modified_calibration = split.calibration.copy()
    modified_calibration["target_available"] = 1 - modified_calibration["target_available"]
    altered_split = replace(split, calibration=modified_calibration)
    altered = train_candidate(
        altered_split, trained.config, status_frame=status, stations=stations, seed=42
    )
    test_features = trained.feature_builder.build(status, split.test).X
    np.testing.assert_allclose(
        np.asarray(trained.model.predict_proba(test_features)),
        np.asarray(altered.model.predict_proba(test_features)),
    )
    assert trained.feature_builder.lag_fill_values == altered.feature_builder.lag_fill_values
    assert trained.hourly_baseline.hourly_rates == altered.hourly_baseline.hourly_rates

    modified_test = split.test.copy()
    modified_test["target_available"] = 1 - modified_test["target_available"]
    test_altered = train_candidate(
        replace(split, test=modified_test),
        trained.config,
        status_frame=status,
        stations=stations,
        seed=42,
    )
    np.testing.assert_allclose(
        trained.predict_proba(test_features), test_altered.predict_proba(test_features)
    )
    assert trained.calibration_method == test_altered.calibration_method
    assert trained.calibration_brier == test_altered.calibration_brier
    assert trained.test_metrics != test_altered.test_metrics


def test_holdout_with_new_seed_holiday_peak_and_outages(trained, stations) -> None:  # noqa: ANN001
    shifted_status = synthetic_status(
        stations,
        seed=123,
        start="2026-10-20T00:00:00+07:00",
        steps=96,
        holiday_peak=0.40,
        outage_probability=0.3,
    )
    shifted_labels = build_labels(shifted_status, [15, 30])
    first = evaluate_holdout(
        trained, shifted_status, shifted_labels, seed=123, source="shifted-simulator"
    )
    assert first.seed == 123
    assert first.source == "shifted-simulator"
    assert first.sample_count == len(shifted_labels)
    assert set(first.metrics) == set(trained.test_metrics)
    assert 0 <= first.metrics["lightgbm_calibrated"].brier_score <= 1
    assert (
        first.metrics["lightgbm_calibrated"].auc is None
        or 0 <= first.metrics["lightgbm_calibrated"].auc <= 1
    )
    assert trained.seed == 42


def test_rejects_unfitted_or_wrong_order_features(trained, setup_training) -> None:  # noqa: ANN001
    status, split = setup_training
    x = trained.feature_builder.build(status, split.test).X
    with pytest.raises(ValueError, match="feature columns|order"):
        trained.predict_proba(x.loc[:, list(reversed(x.columns))])
    with pytest.raises(ValueError, match="feature columns|order"):
        trained.predict_proba(x.drop(columns=x.columns[0]))


@pytest.mark.parametrize(
    "change,error",
    [
        ({"n_estimators": 0}, "n_estimators"),
        ({"learning_rate": 0}, "learning_rate"),
        ({"num_leaves": 1}, "num_leaves"),
        ({"random_state": True}, "random_state"),
        ({"data_type": "mystery"}, "data_type"),
    ],
)
def test_rejects_invalid_training_configuration(change: dict[str, object], error: str) -> None:
    with pytest.raises(ValueError, match=error):
        TrainingConfig(**change)  # type: ignore[arg-type]


def test_rejects_single_class_training_or_calibration(stations, setup_training) -> None:  # noqa: ANN001
    status, split = setup_training
    train = split.train.copy()
    train["target_available"] = 1
    with pytest.raises(ValueError, match="train.*both classes"):
        train_candidate(
            replace(split, train=train), TrainingConfig(), status_frame=status, stations=stations
        )
    calibration = split.calibration.copy()
    calibration["target_available"] = 0
    with pytest.raises(ValueError, match="calibration.*both classes"):
        train_candidate(
            replace(split, calibration=calibration),
            TrainingConfig(),
            status_frame=status,
            stations=stations,
        )
