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

## P0 Dataset and ETA Labels

`dataset.validate_status_frame(frame, stations)` checks canonical simulator snapshots before label generation. Use `labels.build_labels(validated_frame, horizons_minutes)` with unique positive horizons divisible by five minutes. The result contains `station_id`, `scenario`, `observed_at`, `eta`, `horizon_minutes`, and binary `target_available` (`1` iff `ports_free > 0` at the **exact** ETA). Rows without an exact future station/scenario/ETA match are omitted, including when the last snapshot is reached. Missing intermediate snapshots do not change the ETA being labeled. Input frames are not modified.

This label is generated from **future outcomes for supervised training**, not from information available to a prediction at `observed_at`; feature generation and inference must not include future availability. The current station-level status schema aggregates connector types, so these labels only represent compatible-port availability for stations where the aggregate counts are compatible with the requested connector. Mixed-connector stations require connector-specific status and a reviewed contract change before the labels can represent compatibility. Test fixtures are mock/simulated, not measured accuracy evidence.
