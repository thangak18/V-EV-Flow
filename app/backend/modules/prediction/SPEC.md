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

## P0 Deterministic LightGBM Features

`features.FeatureBuilder(stations)` creates an ordered numeric model matrix via
`fit(validated_status, training_labels).build(validated_status, any_split_labels)`.
Call `fit` **only on the chronological training partition** after the time/gap
split; reuse that fitted builder for calibration and test rows. The returned
`FeatureDataset` exposes aligned `frame`, `X`, and `y`; `FEATURE_COLUMNS` defines
the stable, versioned feature order to persist alongside any trained model.

Feature groups: current `ports_free/busy/broken`; the three counts at **exactly**
15, 30, and 60 minutes before `observed_at`; missing indicators for each lag;
cyclical local hour (including minutes), weekday/weekend; scenario one-hot and
holiday-scenario flag; station capacity, power, and urban/highway/other type;
and requested ETA `horizon_minutes`. Station/scenario histories never mix.
Missing lag counts use per-column training-only medians (0 when all training
values are absent); `lag_*_missing` stays 1 so 0 ports is not confused with
missing history. The fitted medians are available as `lag_fill_values` and must
be persisted with the model. Input rows and labels are not modified.

There is no weather or traffic feature without an observed-at-time data source.
`is_holiday_scenario` indicates the simulator scenario (`holiday_30_4` or
`tet`), not an independently verified public-holiday calendar. The input status
must be validated before use; the builder checks joins and label integrity, but
does not replace canonical station-status validation. As with the label builder,
aggregate ports are valid for a compatible single-connector station only. The
training result is from simulated fixtures, not evidence of real-world accuracy.

Verify with `uv run pytest app/backend/modules/prediction -q`, then `make ci`.

## P0 Chronological Split and Label Embargo

`split.temporal_split(dataset, train_end, calibration_end, max_horizon_minutes)`
accepts either a labeled DataFrame or the aligned `FeatureDataset` from the
feature builder. Both cutoffs are timezone-aware `+07:00` timestamps and apply
**globally**, not separately per station or scenario. Splits are ordered by
`observed_at`, then scenario/station/horizon; their row indices restart at 0.

With `gap = max_horizon_minutes`, training observations end at
`train_end - gap` (inclusive); calibration observations start strictly after
`train_end` and end at `calibration_end - gap` (inclusive); test observations
start strictly after `calibration_end`. All observations in
`(train_end - gap, train_end]` and
`(calibration_end - gap, calibration_end]` are embargoed, **including labels
with shorter horizons**. The maximum horizon must be at least as large as
every row's label horizon. Empty partitions, duplicate keys, broken ETA
alignment, invalid timestamps, and misaligned feature matrices are rejected.

`DatasetSplit.metadata` exposes cutoffs, max horizon, sample counts, retained
observation ranges, and rows removed at each embargo. Construct the label
split **before** calling `FeatureBuilder.fit(status, split.train)`; build or
transform remaining rows with the same training-fitted builder. Do not fit
imputation, feature selection, the model, or calibration on future splits.
The embargo guards chronological feature/label overlap, but reported metrics
still describe simulated examples rather than real-world prediction quality.
