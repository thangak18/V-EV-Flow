"""Probability quality diagnostics for supervised ETA-availability models."""

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score


@dataclass(frozen=True)
class CalibrationBin:
    """Fixed-width reliability bin; rates are None when no samples landed in it."""

    lower_bound: float
    upper_bound: float
    count: int
    mean_predicted: float | None
    observed_rate: float | None


@dataclass(frozen=True)
class EvaluationMetrics:
    """Brier/Log Loss/AUC and reliability diagnostics for a single held-out partition."""

    sample_count: int
    positive_count: int
    positive_rate: float
    brier_score: float
    auc: float | None
    calibration: tuple[CalibrationBin, ...]
    ece: float
    log_loss: float | None = None  # None only for legacy artifact reports.


def _vector(value: object, name: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype="float64")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must contain numeric values") from exc
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    return array


def evaluate_probabilities(
    y_true: object, probabilities: object, n_bins: object = 10
) -> EvaluationMetrics:
    """Evaluate aligned outcome/probability vectors with fixed calibration bins.

    Every observed target must be exactly 0 or 1 and every prediction a
    finite number in [0, 1]. AUC is None for single-class evaluation; Brier,
    Log Loss and calibration remain defined. Log Loss declares both binary
    classes and clips probability endpoints using float64 machine epsilon.
    ECE is the count-weighted absolute gap
    between average prediction and observed rate in nonempty bins.

    Bin intervals are [lower, upper), with p=1 included in the final bin.
    These are descriptive metrics, not statistical evidence of real accuracy
    when the source is simulated data.
    """
    if isinstance(n_bins, (bool, np.bool_)) or not isinstance(n_bins, (int, np.integer)):
        raise ValueError("n_bins must be a positive integer")
    bins = int(n_bins)
    if bins <= 0:
        raise ValueError("n_bins must be a positive integer")

    truth = _vector(y_true, "y_true")
    predicted = _vector(probabilities, "probabilities")
    if not truth.size:
        raise ValueError("empty input to probability evaluation")
    if truth.size != predicted.size:
        raise ValueError("y_true and probabilities must have the same length")
    if not np.isin(truth, [0.0, 1.0]).all():
        raise ValueError("y_true must contain only binary labels (0 or 1)")
    if not np.isfinite(predicted).all():
        raise ValueError("probabilities must be finite")
    if (predicted < 0).any() or (predicted > 1).any():
        raise ValueError("probabilities must be in range [0, 1]")

    calibration: list[CalibrationBin] = []
    bin_index = np.minimum((predicted * bins).astype("int64"), bins - 1)
    ece = 0.0
    for index in range(bins):
        subset = bin_index == index
        count = int(subset.sum())
        lower, upper = index / bins, (index + 1) / bins
        if count:
            avg_probability = float(predicted[subset].mean())
            availability = float(truth[subset].mean())
            ece += count / len(truth) * abs(avg_probability - availability)
        else:
            avg_probability = None
            availability = None
        calibration.append(
            CalibrationBin(
                lower_bound=lower,
                upper_bound=upper,
                count=count,
                mean_predicted=avg_probability,
                observed_rate=availability,
            )
        )

    auc = float(roc_auc_score(truth, predicted)) if np.unique(truth).size == 2 else None
    return EvaluationMetrics(
        sample_count=len(truth),
        positive_count=int(truth.sum()),
        positive_rate=float(truth.mean()),
        brier_score=float(brier_score_loss(truth, predicted)),
        log_loss=float(log_loss(truth, predicted, labels=[0, 1])),
        auc=auc,
        calibration=tuple(calibration),
        ece=ece,
    )
