"""Leakage-safe LightGBM training, calibration selection, and baseline comparison.

Call ``temporal_split`` on future-ETA labels before passing the split here.
Only train labels fit the feature imputer, LightGBM, and hourly reference.
Calibration labels fit the two calibrators; their Brier scores select one.
The untouched test period supplies the final four-way score comparison.

All reported results describe the caller's data source. In particular,
simulated scores must not be interpreted as real-world model accuracy.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, cast

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

from app.backend.contracts.stations import Station
from app.backend.modules.prediction.baseline import HourlyRateBaseline, PersistenceBaseline
from app.backend.modules.prediction.features import FEATURE_COLUMNS, FeatureBuilder, FeatureDataset
from app.backend.modules.prediction.metrics import EvaluationMetrics, evaluate_probabilities
from app.backend.modules.prediction.split import DatasetSplit, SplitMetadata

CalibratorName = Literal["isotonic", "platt"]
DataType = Literal["mock", "simulated", "real", "mixed"]


@dataclass(frozen=True)
class TrainingConfig:
    """Pinned, reproducible model parameters and explicit data provenance."""

    random_state: int = 42
    n_estimators: int = 80
    learning_rate: float = 0.05
    num_leaves: int = 15
    max_depth: int = -1
    min_child_samples: int = 8
    reg_lambda: float = 1.0
    data_type: DataType = "simulated"
    source: str = "synthetic-fixture"

    def __post_init__(self) -> None:
        for name in (
            "random_state",
            "n_estimators",
            "num_leaves",
            "max_depth",
            "min_child_samples",
        ):
            value = getattr(self, name)
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
                raise ValueError(f"{name} must be an integer")
        if self.n_estimators < 1:
            raise ValueError("n_estimators must be positive")
        if self.num_leaves < 2:
            raise ValueError("num_leaves must be at least two")
        if self.min_child_samples < 1:
            raise ValueError("min_child_samples must be positive")
        if self.max_depth != -1 and self.max_depth < 1:
            raise ValueError("max_depth must be -1 or positive")
        for name in ("learning_rate", "reg_lambda"):
            value = getattr(self, name)
            if isinstance(value, (bool, np.bool_)) or not isinstance(
                value, (int, float, np.number)
            ):
                raise ValueError(f"{name} must be numeric")
            if (
                not np.isfinite(value)
                or (name == "learning_rate" and value <= 0)
                or (name == "reg_lambda" and value < 0)
            ):
                raise ValueError(f"{name} must be finite and nonnegative (learning_rate > 0)")
        if self.data_type not in ("mock", "simulated", "real", "mixed"):
            raise ValueError("data_type must be mock, simulated, real, or mixed")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be a nonempty data provenance description")


def _log_odds(probabilities: np.ndarray) -> np.ndarray:
    safe = np.clip(probabilities, 1e-6, 1 - 1e-6)
    return np.log(safe / (1 - safe)).reshape(-1, 1)


def _calibrate(
    method: CalibratorName,
    calibrator: IsotonicRegression | LogisticRegression,
    raw_probabilities: np.ndarray,
) -> np.ndarray:
    if method == "isotonic":
        values = cast(IsotonicRegression, calibrator).predict(raw_probabilities)
    else:
        values = cast(LogisticRegression, calibrator).predict_proba(_log_odds(raw_probabilities))[
            :, 1
        ]
    return np.clip(np.asarray(values, dtype="float64"), 0, 1)


def _positive_probabilities(model: LGBMClassifier, features: pd.DataFrame) -> np.ndarray:
    return np.asarray(model.predict_proba(features), dtype="float64")[:, 1]


@dataclass
class TrainedPipeline:
    """In-memory model and report; artifact persistence belongs to artifacts.py."""

    feature_builder: FeatureBuilder
    model: LGBMClassifier
    calibrator: IsotonicRegression | LogisticRegression
    calibration_method: CalibratorName
    hourly_baseline: HourlyRateBaseline
    config: TrainingConfig
    calibration_brier: dict[str, float]
    test_metrics: dict[str, EvaluationMetrics]
    split_metadata: SplitMetadata
    sample_counts: dict[str, int]
    scenarios: tuple[str, ...]
    seed: int | None
    data_type: DataType
    source: str
    feature_columns: tuple[str, ...] = FEATURE_COLUMNS

    def _check_features(self, features: pd.DataFrame | FeatureDataset) -> pd.DataFrame:
        x = features.X if isinstance(features, FeatureDataset) else features
        if not isinstance(x, pd.DataFrame) or tuple(x.columns) != self.feature_columns:
            raise ValueError("feature columns/order do not match the training model")
        if x.empty or bool(x.isna().any().any()):
            raise ValueError("features must be nonempty and have no missing values")
        if not all(pd.api.types.is_numeric_dtype(dtype) for dtype in x.dtypes):
            raise ValueError("features must be numeric")
        if not np.isfinite(x.to_numpy(dtype="float64")).all():
            raise ValueError("features must contain finite values")
        return x

    def predict_proba(self, features: pd.DataFrame | FeatureDataset) -> np.ndarray:
        """Return sklearn-style [P(unavailable), P(available)] in feature order."""
        x = self._check_features(features)
        raw = _positive_probabilities(self.model, x)
        p = _calibrate(self.calibration_method, self.calibrator, raw)
        return np.column_stack((1 - p, p))


@dataclass(frozen=True)
class HoldoutEvaluation:
    """Separate test or shifted-simulator metrics without updating fitted state."""

    metrics: dict[str, EvaluationMetrics]
    sample_count: int
    scenarios: tuple[str, ...]
    observed_range: tuple[pd.Timestamp, pd.Timestamp]
    seed: int | None
    data_type: DataType
    source: str


def _both_classes(y: pd.Series, partition: str) -> None:
    if set(y.unique()) != {0, 1}:
        raise ValueError(f"{partition} requires both classes (0 and 1) to fit the model")


def _compare(pipeline: TrainedPipeline, features: FeatureDataset) -> dict[str, EvaluationMetrics]:
    raw = _positive_probabilities(pipeline.model, pipeline._check_features(features))
    calibrated = _calibrate(pipeline.calibration_method, pipeline.calibrator, raw)
    predictions = {
        "lightgbm_raw": raw,
        "lightgbm_calibrated": calibrated,
        "persistence": PersistenceBaseline().predict_proba(features),
        "hourly_rate": pipeline.hourly_baseline.predict_proba(features),
    }
    return {
        name: evaluate_probabilities(features.y.to_numpy(), values)
        for name, values in predictions.items()
    }


def train_candidate(
    split: DatasetSplit[pd.DataFrame],
    config: TrainingConfig,
    *,
    status_frame: pd.DataFrame,
    stations: Sequence[Station],
    seed: int | None = None,
) -> TrainedPipeline:
    """Fit on embargoed train, select calibration, then score untouched test.

    ``split`` must come directly from ``temporal_split(build_labels(...))``;
    ``status_frame`` must already be validated by ``validate_status_frame``.
    FeatureBuilder's joins read snapshots at or before each observed time.
    Avoid tuning model hyperparameters using returned test metrics.
    """
    if not isinstance(split.train, pd.DataFrame) or not all(
        isinstance(part, pd.DataFrame) for part in (split.calibration, split.test)
    ):
        raise TypeError("training requires a split of labeled DataFrames")
    if not isinstance(config, TrainingConfig):
        raise TypeError("config must be a TrainingConfig")
    if not all(len(part) for part in (split.train, split.calibration, split.test)):
        raise ValueError("train/calibration/test must be nonempty")

    builder = FeatureBuilder(stations).fit(status_frame, split.train)
    training = builder.build(status_frame, split.train)
    calibration = builder.build(status_frame, split.calibration)
    _both_classes(training.y, "train")
    _both_classes(calibration.y, "calibration")

    model = LGBMClassifier(
        objective="binary",
        n_estimators=config.n_estimators,
        learning_rate=config.learning_rate,
        num_leaves=config.num_leaves,
        max_depth=config.max_depth,
        min_child_samples=config.min_child_samples,
        reg_lambda=config.reg_lambda,
        random_state=config.random_state,
        n_jobs=1,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
    )
    model.fit(training.X, training.y)

    calibration_raw = _positive_probabilities(model, calibration.X)
    isotonic = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
    isotonic.fit(calibration_raw, calibration.y.to_numpy())
    platt = LogisticRegression(solver="lbfgs", random_state=config.random_state)
    platt.fit(_log_odds(calibration_raw), calibration.y.to_numpy())
    scores = {
        "isotonic": float(
            brier_score_loss(calibration.y, _calibrate("isotonic", isotonic, calibration_raw))
        ),
        "platt": float(
            brier_score_loss(calibration.y, _calibrate("platt", platt, calibration_raw))
        ),
    }
    # Isotonic strictly wins only if its calibration Brier is lower.
    # Equal values deterministically select Platt, regardless of test outcomes.
    method: CalibratorName = "isotonic" if scores["isotonic"] < scores["platt"] else "platt"
    calibrator = isotonic if method == "isotonic" else platt
    hourly = HourlyRateBaseline().fit(training)
    scenarios = tuple(sorted(set(split.train["scenario"].astype(str))))
    pipeline = TrainedPipeline(
        feature_builder=builder,
        model=model,
        calibrator=calibrator,
        calibration_method=method,
        hourly_baseline=hourly,
        config=config,
        calibration_brier=scores,
        test_metrics={},
        split_metadata=split.metadata,
        sample_counts=split.metadata.counts.copy(),
        scenarios=scenarios,
        seed=seed,
        data_type=config.data_type,
        source=config.source,
    )
    # Every fit and every calibration choice is finished before test is read.
    test = builder.build(status_frame, split.test)
    pipeline.test_metrics = _compare(pipeline, test)
    return pipeline


def evaluate_holdout(
    pipeline: TrainedPipeline,
    status_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    seed: int | None = None,
    source: str,
    data_type: DataType = "simulated",
) -> HoldoutEvaluation:
    """Evaluate on a separate timeline/seed; never refit or choose calibration."""
    if not source.strip():
        raise ValueError("holdout source must be nonempty")
    if data_type not in ("mock", "simulated", "real", "mixed"):
        raise ValueError("invalid holdout data_type")
    features = pipeline.feature_builder.build(status_frame, labels)
    observed = features.frame["observed_at"]
    return HoldoutEvaluation(
        metrics=_compare(pipeline, features),
        sample_count=len(features.frame),
        scenarios=tuple(sorted(set(features.frame["scenario"].astype(str)))),
        observed_range=(cast(pd.Timestamp, observed.min()), cast(pd.Timestamp, observed.max())),
        seed=seed,
        data_type=data_type,
        source=source,
    )
