# Prediction CLI verification

Owner: Thắng. Branch: `feat/ml-predict`. PR remains Draft.

Executed `uv run python -m app.backend.modules.prediction.cli` with each of
`train`, `evaluate`, and `predict` on local temporary CSV/JSON fixtures. All
three exited 0. Input and artifact files live under `/tmp/v-ev-ml-cli-demo`;
they are not committed. The full command syntax is documented in SPEC.md.

Source: an independent-snapshot synthetic smoke fixture with NumPy seed 33,
one 4-port CCS2 station, normal/tet scenarios and 400 five-minute steps each.
This is not Bảo's stateful simulator or partner data and has no measured road
accuracy meaning. The evaluation fixture shifts the timeline by ten days;
it checks CLI isolation rather than a novel distribution/seed. Separate shifted
seed/pressure/outage tests exist in `test_training.py`.

Train/calibration/test counts: 412/456/666. Train cutoff
2026-10-12T09:00:00+07:00; calibration cutoff 2026-10-12T19:00:00+07:00.
Horizons 15/30 minutes; maximum-horizon embargo 30 minutes. Holdout: 1582 labels.

| Test predictor | Brier | AUC |
| --- | --- | --- |
| LightGBM raw | 0.146814 | 0.473464 |
| LightGBM calibrated | 0.145354 | 0.477784 |
| Persistence | 0.253754 | 0.508777 |
| Hourly rate | 0.142375 | 0.421400 |

The hourly baseline has lower Brier than LightGBM here. These smoke results
verify the workflow and do not establish model superiority.

Sample inference: S001, observed 2026-10-13T00:00:00+07:00, ETA
2026-10-13T00:30:00+07:00, normal/CCS2, p_available 0.9242424242424242,
model_version `lightgbm-b9b2ef7801fe391e`, data_type `simulated`,
explanation_method `rule`, contract_version `0.1.0`.

Verification:

- `uv run pytest app/backend/modules/prediction -q`: 148 passed.
- `uv run ruff check app/backend/modules/prediction`: passed.
- `uv run pyright app/backend/modules/prediction`: 0 errors.
- `PYTEST_ADDOPTS='app/backend/modules/prediction/tests' make ci`: exit 0;
  206 backend tests, 94% aggregate coverage, 12 frontend tests and 1 E2E passed.
  Seven existing non-fatal Redocly warnings remain. Audits found no vulnerabilities.

Limitations: trusted local joblib only; single compatible connector aggregates;
exact current status required; API integration remains the backend owner's work.
Rollback: revert this domain branch's feature commits and use the Phase 0 fake
predictor. Model binaries and histories remain outside Git.
