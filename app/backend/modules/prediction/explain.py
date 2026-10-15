"""Native LightGBM TreeSHAP over the pre-calibration binary raw margin."""

from math import exp

import numpy as np
import pandas as pd

from app.backend.contracts.explanations import FeatureContribution, ModelExplanation
from app.backend.modules.prediction.training import TrainedPipeline


def explain_prediction(
    pipeline: TrainedPipeline, features: pd.DataFrame, calibrated_probability: float
) -> ModelExplanation:
    if len(features) != 1:
        raise ValueError("a local explanation requires exactly one feature row")
    booster = pipeline.model.booster_
    contributions = np.asarray(
        booster.predict(features, pred_contrib=True, num_threads=1), dtype=float
    )
    raw = float(np.asarray(booster.predict(features, raw_score=True, num_threads=1))[0])
    if (
        contributions.shape != (1, len(features.columns) + 1)
        or not np.isfinite(contributions).all()
    ):
        raise ValueError("unexpected native TreeSHAP shape or non-finite contributions")
    probability = 1 / (1 + exp(-raw)) if raw >= 0 else exp(raw) / (1 + exp(raw))
    return ModelExplanation(
        bias=float(contributions[0, -1]),
        raw_score=raw,
        raw_probability=probability,
        calibrated_probability=calibrated_probability,
        features=tuple(
            FeatureContribution(
                feature=str(name),
                value=float(features.iloc[0][name]),
                contribution=float(contributions[0, index]),
            )
            for index, name in enumerate(features.columns)
        ),
    )
