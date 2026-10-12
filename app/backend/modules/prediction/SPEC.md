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

## P0 Baselines and Probability Metrics

`baseline.PersistenceBaseline().predict_proba(evaluation)` predicts 1.0 when
`ports_free > 0` at the **observation time**, otherwise 0.0. It is a deliberately
simple reference for a requested ETA and never consults outcome labels. The
counts must already represent ports compatible with the requested connector;
aggregate station counts are insufficient at mixed-connector sites.

`baseline.HourlyRateBaseline().fit(train).predict_proba(evaluation)` learns the
mean binary training target **by local ETA hour (+07:00)**. An hour with no
training examples falls back to the global training positive rate. Call `fit`
**once on the embargoed training partition only**; predictions require only
known ETA timestamps. Both baselines accept labeled DataFrames or aligned
`FeatureDataset` frames and return one probability per row.

`metrics.evaluate_probabilities(y_true, probabilities, n_bins=10)` returns an
`EvaluationMetrics` record with `sample_count`, `positive_count`,
`positive_rate`, `brier_score`, `auc`, `calibration`, and `ece`. AUC is `None`
for single-class partitions; Brier and calibration still apply. Calibration
uses fixed-width probability bins `[lower, upper)` with 1.0 in the last bin,
each recording sample count, mean predicted probability, and observed rate.
Empty bins have count 0 and nullable rates; ECE is the sample-count-weighted
mean absolute reliability gap. Scores from mock/simulated fixtures demonstrate
pipeline behavior, **not** real-world predictive performance.

## P0 LightGBM Training and Calibration

`training.train_candidate(split, config, status_frame=validated_status, stations=stations,
seed=seed)` accepts the **labeled DataFrame split** returned by
`temporal_split`. The training partition exclusively fits lag imputations,
`LGBMClassifier`, and `HourlyRateBaseline`. LightGBM runs with explicit
`TrainingConfig` hyperparameters, a fixed random seed, one worker, and
deterministic histogram settings.

Predictions for the calibration partition train two post-hoc calibrators:
isotonic regression on raw probabilities and Platt scaling (logistic
regression on clipped log-odds). Select the lower **calibration** Brier score;
ties select Platt. Do not fit or choose anything based on test outcomes.
Only after choosing a calibrator, score the held-out test period once with
`lightgbm_raw`, `lightgbm_calibrated`, `persistence`, and `hourly_rate`.

`TrainedPipeline` keeps the fitted feature builder, model, calibrator,
training config, both calibration Brier scores, test metrics, split metadata,
sample counts, feature-column order, scenarios, source, data type, and seed.
Its `predict_proba` requires a finite, numeric, complete feature matrix in
the exact training order and returns two columns: `P(unavailable)` and
`P(available)`. Serialization and serving are separate subsequent tasks.

`evaluate_holdout(pipeline, validated_status, labels, source=..., seed=...)`
scores a completely separate simulator seed/timeline or later external
dataset using frozen model, calibrator, and reference rates. Use it to test
increased holiday demand and outage pressure; do not refit on that holdout.
Always label reported results by their source and `mock` / `simulated` /
`real` / `mixed` provenance. These synthetic checks establish workflow
correctness, not measured road-network performance.

## P0 Versioned Model Artifacts

`artifacts.save_pipeline(trained_pipeline, directory, data_version=...,
fixture_hash=...)` saves the fitted LightGBM, chosen calibrator, feature
builder (including training-only lag imputations), hourly baseline and test
report as **one compressed joblib binary**. It returns a `ModelManifest` and
writes `manifest.json` beside a content-addressed
`model-<sha256>.joblib`. Binary names contain their SHA-256 and manifest
publication occurs last via atomic replacement; earlier binaries remain so
an interrupted replacement does not invalidate the existing manifest.

The JSON manifest records schema/contract/model versions, creation time,
binary checksum, LightGBM and calibrator classes, calibration method,
ordered features and lag medians, configuration, split ranges and embargo
counts, calibration scores, all four test metric summaries, scenario/seed,
data type, source, data version and optional input fixture hash. Pass a real
SHA-256 input digest when available; otherwise `fixture_hash` is explicitly
`null` and `data_version` defaults to `unspecified` rather than claiming
measured provenance.

`artifacts.read_manifest(directory)` inspects metadata without unpickling.
`artifacts.load_pipeline(directory, expected_contract_version="0.1.0")`
checks supported schema, expected contract version, current `FEATURE_COLUMNS`
order, safe binary filename and SHA-256 **before** joblib deserialization,
then checks that stored metadata agrees with the loaded pipeline. Recovered
models preserve probability predictions and calibration. Joblib uses pickle:
only load files from a trusted producer; the manifest's hash detects
corruption but is not a signature/authenticity guarantee. Model binaries
remain Git-ignored. Do not commit them or simulated/generated histories.

## P0 Runtime Predictor and CLI

`public.load_predictor(model_dir, status_repository, station_repository,
status_data_type=DataType.SIMULATED)` binds the shared repository ports to a
calibrated `ModelPredictor`. Status provenance must be explicitly supplied for
non-mock sources because contract v0 `StatusWindow` has no provenance field.
Different training/status data types produce `mixed`. Reasons give rule-based
context and identify sources; they do not claim per-sample SHAP explanations.

The status repository must accept `lags=(0, 15, 30, 60)` and return the exact
current snapshot plus available historical snapshots for the requested station
and scenario. Missing past lags use persisted training medians. Missing current,
future/unrequested snapshots, scenario mismatches, unsupported connectors,
mixed-connector aggregate counts and changed station capacity/power/type are
rejected. Request times use +07:00; observation and positive horizon align to
five-minute buckets, with horizon bounded by the model split configuration.
The existing Phase 0 mock repository omits lag 0 by default, so its caller must
request that lag explicitly. API composition remains Kiên's responsibility.

Run the CLI from the repository root (paths below refer to caller-provided
local files; no generated histories or binaries are committed):

```bash
uv run python -m app.backend.modules.prediction.cli train \
  --stations /path/stations.json --status /path/status.parquet \
  --artifact-dir app/backend/modules/prediction/artifacts/demo \
  --train-end '2026-10-12T09:00:00+07:00' \
  --calibration-end '2026-10-12T19:00:00+07:00' \
  --horizons 15,30,60 --source bao-simulator --data-type simulated \
  --data-version simulator-v1 --seed 42

uv run python -m app.backend.modules.prediction.cli evaluate \
  --stations /path/stations.json --status /path/later-holdout.parquet \
  --model-dir app/backend/modules/prediction/artifacts/demo \
  --horizons 15,30,60 --source separate-simulator --data-type simulated --seed 91

uv run python -m app.backend.modules.prediction.cli predict \
  --stations /path/stations.json --status /path/status.parquet \
  --model-dir app/backend/modules/prediction/artifacts/demo \
  --station-id S001 --observed-at '2026-10-13T00:00:00+07:00' \
  --eta '2026-10-13T00:30:00+07:00' --connector-type CCS2 \
  --scenario normal --status-data-type simulated
```

Station input is a JSON array; histories accept canonical CSV or Parquet.
Training cutoffs are explicit rather than inferred from machine time. Seed
controls LightGBM; it does not generate or resample caller histories. The
manifest fixture digest hashes actual station/history bytes with length framing.
Commands emit JSON on stdout; invalid inputs/artifacts return exit code 2 and
JSON errors on stderr. Train reports four-way test metrics, split counts/ranges
and artifact path; evaluate reports separate holdout metrics without refitting.
CLI evaluation requires a later timeline beyond the original test observations
and horizons no larger than the training maximum. Use `evaluate_holdout` directly
for deliberately controlled alternate-seed experiments on other timelines.
Synthetic CLI smoke tests demonstrate workflow correctness, not road accuracy.

Verification: `uv run pytest app/backend/modules/prediction -q` and
`PYTEST_ADDOPTS='app/backend/modules/prediction/tests' make ci` include domain
unit tests alongside the foundation checks without changing shared tooling.
