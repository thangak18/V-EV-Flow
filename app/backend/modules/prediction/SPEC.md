# Prediction Module Specification — B/Thắng

## Objective

Produce calibrated probability that a compatible working port is available at ETA, using only information available at `observed_at`, and expose it through the shared `Predictor` port.

## Inputs and Public Output

Inputs are canonical station/status data and scenario metadata. Outputs are feature datasets/manifests, baseline and model evaluation, model/calibrator metadata, and `PredictionResult` with probability, reasons/explanation method, model version, and data type.

## Invariants

The label is availability at `t+h`; feature values stop at `t`. Train, calibration, and test splits are chronological with a gap at least equal to maximum horizon. Model feature order and versions are persisted. Model binary artifacts remain ignored; CI uses a fake predictor or tiny test fixture, not a committed production artifact.

## Freedom and Non-goals

Thắng chooses feature code, LightGBM parameters, and isotonic versus Platt based on validation. The module does not rank stations, call routes, write API handlers, or read simulator private state. SHAP and time-shift are P1.

## Required Tests and Done Criteria

Test label alignment, lag boundaries, split leakage, deterministic features, missing windows, probability range, artifact compatibility, and Predictor conformance. Report sample counts, AUC when both classes exist, Brier score, calibration, and persistence baseline. Results must state that simulated evaluation is not real-world accuracy.
