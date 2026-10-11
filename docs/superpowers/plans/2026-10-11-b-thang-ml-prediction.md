# B/Thắng ML Prediction Implementation Plan

> **For agentic workers:** Use the repository-owned [harness workflow](../../harness/workflow.md), applicable AGENTS/SPEC and assigned issue AC. Track task checkboxes as implementation notes; no external skill/plugin is required. Evidence and handoff follow the common workflow.

**Goal:** Build a leakage-safe, calibrated ETA-availability prediction pipeline and expose it through the shared `Predictor` port.

**Architecture:** The prediction module converts canonical station/status windows into deterministic features and horizon labels, splits chronologically with a gap, evaluates persistence and LightGBM, calibrates on a separate split, and stores a versioned manifest plus ignored binary artifacts. Runtime inference depends only on contract DTOs and artifact metadata.

**Tech Stack:** Python 3.11, pandas, NumPy, LightGBM, scikit-learn, joblib, Pydantic contracts, pytest.

**Spec:** `app/backend/modules/prediction/SPEC.md` and `docs/ML_AND_ALLOCATION.md`

## Global Constraints

- Start `feat/ml-predict` from the green Phase 0 merge SHA.
- Edit only `app/backend/modules/prediction`, its tests/docs, and ignored prediction artifacts.
- Do not edit simulator, recommendation, API, infrastructure, frontend, shared contracts, OpenAPI, or root tooling.
- Use only information available at `observed_at`; no random snapshot split and no future leakage.
- Train, calibration, and test are chronological with a gap at least equal to maximum horizon.
- Model binaries remain ignored; manifests and small evaluation summaries are reviewable.
- Simulated results must not be described as real-world accuracy.
- Every task uses red-green-refactor and a focused commit.

## File Map

```text
app/backend/modules/prediction/dataset.py       Contract-to-frame validation
app/backend/modules/prediction/labels.py        Availability-at-horizon labels
app/backend/modules/prediction/features.py      Snapshot/lag/calendar features
app/backend/modules/prediction/split.py         Chronological split with gap
app/backend/modules/prediction/baseline.py      Persistence/hourly baselines
app/backend/modules/prediction/metrics.py       AUC/Brier/calibration summaries
app/backend/modules/prediction/training.py      LightGBM and calibrator fitting
app/backend/modules/prediction/artifacts.py     Manifest and joblib persistence
app/backend/modules/prediction/predictor.py     Predictor port implementation
app/backend/modules/prediction/cli.py           Train/evaluate/infer commands
app/backend/modules/prediction/public.py        Stable exports
```

---

### Task 1: Validate Canonical Training Data

**Files:**
- Create: `app/backend/modules/prediction/__init__.py`
- Create: `app/backend/modules/prediction/dataset.py`
- Create: `app/backend/modules/prediction/tests/test_dataset.py`

**Interfaces:**
- Produces: `load_status_frame(path: Path) -> pd.DataFrame` and `validate_status_frame(frame, stations) -> pd.DataFrame`.

- [ ] **Step 1: Write failing dataset validation tests**

```python
def test_status_rows_are_unique_per_scenario_station_time(valid_frame, stations) -> None:
    duplicate = pd.concat([valid_frame, valid_frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="unique"):
        validate_status_frame(duplicate, stations)


def test_status_counts_equal_station_capacity(valid_frame, stations) -> None:
    invalid = valid_frame.copy()
    invalid.loc[0, "ports_free"] += 1
    with pytest.raises(ValueError, match="capacity"):
        validate_status_frame(invalid, stations)
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/prediction/tests/test_dataset.py -v`

Expected: FAIL because dataset module does not exist.

- [ ] **Step 3: Implement schema, sort, timezone, and capacity validation**

Require exact status columns, join station capacities by stable ID, reject unknown stations/negative counts/naive times/duplicate keys, and return a sorted copy. Do not mutate caller frames.

- [ ] **Step 4: Run tests**

Run: `uv run pytest app/backend/modules/prediction/tests/test_dataset.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/prediction
git commit -m "feat(ml): validate canonical status data"
```

### Task 2: Build Horizon Labels Without Leakage

**Files:**
- Create: `app/backend/modules/prediction/labels.py`
- Create: `app/backend/modules/prediction/tests/test_labels.py`

**Interfaces:**
- Produces: `build_labels(frame: pd.DataFrame, horizons_minutes: Sequence[int]) -> pd.DataFrame` with `observed_at`, `eta`, `horizon_minutes`, and binary `target_available`.

- [ ] **Step 1: Write failing alignment tests**

```python
def test_label_uses_status_at_observed_plus_horizon(status_frame) -> None:
    labels = build_labels(status_frame, horizons_minutes=[30])
    row = labels.query("station_id == 'S001' and observed_at == @T0").iloc[0]
    expected = status_frame.query("station_id == 'S001' and ts == @T0_PLUS_30").iloc[0]
    assert row.target_available == int(expected.ports_free > 0)
```

Also test that rows without a future exact 5-minute timestamp are dropped and connector compatibility is respected when connector-level status exists.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/prediction/tests/test_labels.py -v`

Expected: FAIL because label builder does not exist.

- [ ] **Step 3: Implement station/scenario grouped shifts**

Convert horizon to step counts only after verifying divisibility by the 5-minute interval. Use grouped negative shift for future availability and retain `observed_at`; never merge to the nearest future row.

- [ ] **Step 4: Run tests**

Run: `uv run pytest app/backend/modules/prediction/tests/test_labels.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/prediction/labels.py app/backend/modules/prediction/tests/test_labels.py
git commit -m "feat(ml): build ETA availability labels"
```

### Task 3: Build Deterministic Snapshot and Lag Features

**Files:**
- Create: `app/backend/modules/prediction/features.py`
- Create: `app/backend/modules/prediction/tests/test_features.py`

**Interfaces:**
- Produces: `FeatureBuilder.build(frame, labels) -> FeatureDataset` and constant `FEATURE_COLUMNS` preserving inference order.

- [ ] **Step 1: Write failing feature tests**

```python
def test_lag_feature_never_reads_after_observed_at(status_frame, labels) -> None:
    dataset = FeatureBuilder().build(status_frame, labels)
    row = dataset.frame.iloc[0]
    assert row["ports_free_lag_15"] == status_at(row.station_id, row.observed_at - MINUTES_15).ports_free


def test_feature_column_order_is_stable(status_frame, labels) -> None:
    assert list(FeatureBuilder().build(status_frame, labels).X.columns) == list(FEATURE_COLUMNS)
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/prediction/tests/test_features.py -v`

Expected: FAIL because feature builder does not exist.

- [ ] **Step 3: Implement P0 features**

Include current free/busy/broken ports, 15/30/60-minute lags, hour cyclical encoding, weekday, holiday/scenario flags, station capacity/power/type, and horizon. Leave weather and traffic absent unless a source available at decision time is added through a later contract change.

- [ ] **Step 4: Define explicit missing-lag behavior**

Add missing indicators and a deterministic numeric fill learned from training data; do not backfill from future rows.

- [ ] **Step 5: Run tests**

Run: `uv run pytest app/backend/modules/prediction/tests/test_features.py -v`

Expected: PASS for lag values, boundaries, no mutation, feature order, and missing indicators.

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/prediction/features.py app/backend/modules/prediction/tests/test_features.py
git commit -m "feat(ml): create leakage-safe features"
```

### Task 4: Implement Chronological Train/Calibration/Test Splits

**Files:**
- Create: `app/backend/modules/prediction/split.py`
- Create: `app/backend/modules/prediction/tests/test_split.py`

**Interfaces:**
- Produces: `temporal_split(dataset, train_end, calibration_end, max_horizon_minutes) -> DatasetSplit`.

- [ ] **Step 1: Write failing split-gap tests**

```python
def test_split_gap_prevents_label_overlap(dataset) -> None:
    split = temporal_split(dataset, train_end=TRAIN_END,
                           calibration_end=CAL_END, max_horizon_minutes=60)
    assert split.train.eta.max() < split.calibration.observed_at.min()
    assert split.calibration.eta.max() < split.test.observed_at.min()
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/prediction/tests/test_split.py -v`

Expected: FAIL because split module does not exist.

- [ ] **Step 3: Implement stable chronological splits**

Sort by observed time/station, apply a 60-minute embargo by removing boundary rows whose ETA crosses the next split, reject empty partitions, and return counts/time ranges in metadata.

- [ ] **Step 4: Run tests**

Run: `uv run pytest app/backend/modules/prediction/tests/test_split.py -v`

Expected: PASS for gaps, order, empty-range error, and reproducible counts.

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/prediction/split.py app/backend/modules/prediction/tests/test_split.py
git commit -m "feat(ml): add embargoed temporal splits"
```

### Task 5: Establish Baselines and Metrics

**Files:**
- Create: `app/backend/modules/prediction/baseline.py`
- Create: `app/backend/modules/prediction/metrics.py`
- Create: `app/backend/modules/prediction/tests/test_metrics.py`

**Interfaces:**
- Produces: `PersistenceBaseline`, `HourlyRateBaseline`, and `evaluate_probabilities(y_true, probabilities) -> EvaluationMetrics`.

- [ ] **Step 1: Write failing metric tests**

```python
def test_brier_score_matches_known_values() -> None:
    metrics = evaluate_probabilities(np.array([0, 1]), np.array([0.25, 0.75]))
    assert metrics.brier_score == pytest.approx(0.0625)


def test_auc_is_none_when_test_has_one_class() -> None:
    metrics = evaluate_probabilities(np.ones(4), np.full(4, 0.8))
    assert metrics.auc is None
    assert metrics.sample_count == 4
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/prediction/tests/test_metrics.py -v`

Expected: FAIL because baseline/metrics modules do not exist.

- [ ] **Step 3: Implement honest probability metrics**

Use sklearn Brier/AUC, calibration bins with counts, and explicit one-class handling. Persistence probability is current compatible availability; hourly rate learns only from training rows.

- [ ] **Step 4: Run tests**

Run: `uv run pytest app/backend/modules/prediction/tests/test_metrics.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/prediction/baseline.py app/backend/modules/prediction/metrics.py app/backend/modules/prediction/tests/test_metrics.py
git commit -m "feat(ml): add probability baselines and metrics"
```

### Task 6: Train LightGBM and Select Calibration

**Files:**
- Create: `app/backend/modules/prediction/training.py`
- Create: `app/backend/modules/prediction/tests/test_training.py`

**Interfaces:**
- Produces: `train_candidate(split, config) -> TrainedPipeline` containing feature builder state, LightGBM model, chosen calibrator, metrics, and config.

- [ ] **Step 1: Write failing synthetic training tests**

Assert probabilities are bounded, model fit uses train only, calibrator fit uses calibration only, test data is touched only by final evaluation, and fixed config produces identical predictions.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/prediction/tests/test_training.py -v`

Expected: FAIL because training module does not exist.

- [ ] **Step 3: Implement deterministic LightGBM training**

Set `random_state`, `n_jobs=1` for reproducible CI tests, and explicit hyperparameters in `TrainingConfig`. Fit candidates on train; fit isotonic and Platt candidates on calibration predictions; choose the lower calibration Brier score with deterministic tie-break `platt`.

- [ ] **Step 4: Evaluate once on test**

Return model, persistence baseline, hourly baseline, uncalibrated/calibrated metrics, sample counts, split ranges, and scenario/seed metadata. Never choose hyperparameters from test metrics.

- [ ] **Step 5: Evaluate a shifted simulator configuration**

Build a synthetic holdout with a different seed, stronger holiday peak, and higher outage rate than training. Assert evaluation completes, record its Brier/AUC/sample counts separately, and never concatenate it back into training or calibration.

- [ ] **Step 6: Run tests**

Run: `uv run pytest app/backend/modules/prediction/tests/test_training.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/backend/modules/prediction/training.py app/backend/modules/prediction/tests/test_training.py
git commit -m "feat(ml): train and calibrate availability model"
```

### Task 7: Persist Versioned Artifacts and Manifests

**Files:**
- Create: `app/backend/modules/prediction/artifacts.py`
- Create: `app/backend/modules/prediction/tests/test_artifacts.py`

**Interfaces:**
- Produces: `save_pipeline(pipeline, directory) -> ModelManifest` and `load_pipeline(directory, expected_contract_version) -> TrainedPipeline`.

- [ ] **Step 1: Write failing artifact compatibility tests**

Test round-trip prediction equality, feature-order preservation, SHA-256 verification, rejected contract-version mismatch, and rejected missing binary.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/prediction/tests/test_artifacts.py -v`

Expected: FAIL because artifact store does not exist.

- [ ] **Step 3: Implement manifest and atomic writes**

Manifest includes model/calibrator class, `model_version`, `contract_version`, feature columns, training config, split ranges, metrics, fixture hash, data version, created timestamp, and binary SHA-256. Write to a temporary path and rename after success.

- [ ] **Step 4: Verify Phase 0 ignore rules and keep manifests reviewable**

Confirm `git check-ignore app/backend/modules/prediction/artifacts/model.joblib` succeeds. CLI may copy a small JSON manifest to a PR evidence directory without adding binary files; do not edit root `.gitignore` in this feature branch.

- [ ] **Step 5: Run tests**

Run: `uv run pytest app/backend/modules/prediction/tests/test_artifacts.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/prediction/artifacts.py app/backend/modules/prediction/tests/test_artifacts.py
git commit -m "feat(ml): version prediction artifacts"
```

### Task 8: Implement the Runtime Predictor Port

**Files:**
- Create: `app/backend/modules/prediction/predictor.py`
- Create: `app/backend/modules/prediction/public.py`
- Create: `app/backend/modules/prediction/tests/test_predictor.py`

**Interfaces:**
- Produces: `ModelPredictor.predict(request: PredictRequest) -> PredictionResult` and public `load_predictor(model_dir: Path, status_repository: StatusRepository, station_repository: StationRepository) -> Predictor`.

- [ ] **Step 1: Write failing inference tests**

Test exact ETA horizon calculation, station lookup, lag-window usage, feature order, missing/out-of-range horizon error, bounded calibrated output, and source/model versions.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/prediction/tests/test_predictor.py -v`

Expected: FAIL because runtime predictor does not exist.

- [ ] **Step 3: Implement inference without future access**

```python
def predict(self, request: PredictRequest) -> PredictionResult:
    horizon = int((request.eta - request.observed_at).total_seconds() // 60)
    window = self.status_source.window(request.station_id, request.observed_at, lags=(15, 30, 60))
    features = self.feature_builder.for_request(request, window, horizon)
    probability = float(self.pipeline.predict_proba(features)[0, 1])
    return PredictionResult(
        station_id=request.station_id,
        eta=request.eta,
        p_available=probability,
        reasons=[f"Calibrated prediction for a {horizon}-minute horizon"],
        explanation_method="rule",
        model_version=self.manifest.model_version,
        data_type=window.data_type,
        contract_version=self.manifest.contract_version,
    )
```

P0 reasons are rule-based and labelled `explanation_method="rule"`; do not claim global feature importance explains an individual row.

- [ ] **Step 4: Run predictor tests**

Run: `uv run pytest app/backend/modules/prediction/tests/test_predictor.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/prediction/predictor.py app/backend/modules/prediction/public.py app/backend/modules/prediction/tests/test_predictor.py
git commit -m "feat(ml): expose calibrated predictor port"
```

### Task 9: Add Train/Evaluate/Infer CLIs and Handoff Evidence

**Files:**
- Create: `app/backend/modules/prediction/cli.py`
- Create: `app/backend/modules/prediction/tests/test_cli.py`
- Modify: `app/backend/modules/prediction/SPEC.md`

**Interfaces:**
- Produces: `train`, `evaluate`, and `predict` CLI subcommands with explicit input/output/version arguments.

- [ ] **Step 1: Write failing CLI smoke tests**

Use a small synthetic fixture in `tmp_path`; run train, evaluate, and predict; assert manifest/evaluation JSON validate and prediction contains bounded probability and matching versions.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/prediction/tests/test_cli.py -v`

Expected: FAIL because CLI does not exist.

- [ ] **Step 3: Implement commands and machine-readable summaries**

Use argparse, return non-zero for invalid data/artifacts, and print only a concise JSON summary plus output paths. Defaults use seed 42 and documented split dates derived from fixture range.

- [ ] **Step 4: Run the owner gate**

```bash
uv run pytest app/backend/modules/prediction -v
uv run ruff check app/backend/modules/prediction
uv run pyright app/backend/modules/prediction
make lint
```

Expected: PASS without committing model binaries.

- [ ] **Step 5: Commit and open PR**

```bash
git add app/backend/modules/prediction
git commit -m "docs(ml): finalize prediction handoff"
```

PR evidence includes manifest, sample counts, temporal ranges/gaps, baseline and calibrated Brier/AUC, calibration table/plot artifact, one inference response, simulator/data versions, and explicit simulated-data limitation.
