# Fix Operator simulation latency and scenario re-selection

Serving data remains **simulated**, using the unchanged V2 model
`lightgbm-0e9c6bb20db734dd` and capacity variant
`lightgbm-f01a2875bada1b0d`. Paris remains an offline benchmark.

## Diagnosed causes

The old Predictor reconstructed supervised label/status DataFrames, validated
those tables, and executed current/lag/metadata joins for every single candidate
prediction. A 100-vehicle run repeatedly paid this training-table overhead.
Thread-stack snapshots showed inference in pandas construction/indexing and
PyArrow conversion. Simulation's existing request lock serializes comparisons,
so a slow AI run also delays subsequent simulation work. This evidence does not
establish a native OpenMP deadlock.

A separate UI defect disabled Apply after re-selecting the already active
scenario: runtimeReady was cleared even though React did not change scenario,
so the effect that would restore readiness never ran.

## Changes

- Validate the exact current and historical window directly: scenario/station,
  timestamps, duplicate keys, integer/nonnegative counts and capacity remain
  checked. Future/unrequested snapshots and unsupported horizons remain rejected.
- Build the same ordered numeric features directly from those validated snapshots,
  immutable training station metadata and persisted training-only lag medians.
  Missing indicators and calendar/scenario encodings match the training builder.
  No supervised label or future outcome is needed in serving.
- Keep the batch builder as the independent reference. Nine regression cases
  compare every feature and model probability across all three scenarios and
  complete/partially missing/fully missing past lags (absolute tolerance 1e-12).
- Ignore a scenario change event whose value is already selected. A frontend
  regression test failed before this guard and passes after it.

No model retraining, feature order/version, threshold, API contract, simulation
seed/population, concurrency lock or browser timeout is changed.

## Executed evidence

Same V2 artifact, Tết, seed 42, 100 vehicles on the local Mac:

- Original inference did not complete within a 90-second isolated HTTP timeout.
- Removing batch joins while retaining pandas window validation: HTTP 200 in
  21.89 seconds.
- Direct validated-window inference: HTTP 200 in 1.66 seconds. Metrics matched
  the intermediate run: success rate 0.63, mean wait 7.9 minutes, 11 failed,
  mean detour 10.821614920999412 km, population 100. Timings are local samples,
  not a latency guarantee or measurements of real traffic.

Focused prediction plus runtime integration suite: **215 passed**. Operator
frontend suite: **5 passed**. Real-artifact browser suite: **4 passed**, about
1.1 minutes, with actual model/calibrator, Goong maps/routing, SQLite allocation
and stateful simulator, without injected API responses:

1. Driver: TreeSHAP reconstruction, calibrated probability, map marker and
   time-shift evaluation.
2. Operator Tết comparison and both what-if kinds: added-capacity model version,
   unchanged fixture/seed/population and exactly twenty shifted vehicles.
3. Driver API/UI probability and simulated provenance.
4. All three scenarios, three strategies each, 100 vehicles, shared fixture hash
   per comparison and correct model/baseline versions.

Full clean-revision `make ci` is recorded in the final task handoff and ignored
local verification artifacts. Logs/screenshots/videos stay outside Git.

Rollback: revert this fix to restore the previous serving/UI paths. Release
binaries and histories are unchanged. Real partner accuracy and physical
reservations remain unverified; these fixes accept the simulated demo flow.
