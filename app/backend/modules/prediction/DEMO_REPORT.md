# Synthetic Predictor integration demo

Synthetic correlated per-port timers; no queues, routes or strategy evaluation.
Not Bảo's simulator, partner data, or evidence of real-world accuracy.

Source/data version: synthetic-correlated-integration-demo-v1; seed: 42; days: 7.
Model version: lightgbm-a92536a3b5c32ca1; calibration: isotonic.
Rows: 18144; split counts: {'train': 32346, 'calibration': 10557, 'test': 10692}.
Embargo: 60 minutes; split metadata: {'train_end': '2026-10-16T04:48:00+07:00', 'calibration_end': '2026-10-17T14:24:00+07:00', 'max_horizon_minutes': 60, 'counts': {'train': 32346, 'calibration': 10557, 'test': 10692}, 'observed_ranges': {'train': ['2026-10-12T00:00:00+07:00', '2026-10-16T03:45:00+07:00'], 'calibration': ['2026-10-16T04:50:00+07:00', '2026-10-17T13:20:00+07:00'], 'test': ['2026-10-17T14:25:00+07:00', '2026-10-18T23:40:00+07:00']}, 'dropped_for_embargo': {'train': 324, 'calibration': 324}}.

| Predictor | Brier ↓ | Log Loss ↓ | AUC ↑ | ECE ↓ | Samples |
| --- | --- | --- | --- | --- | --- |
| lightgbm_raw | 0.181507 | 0.540818 | 0.7534505209161458 | 0.021825 | 10692 |
| lightgbm_calibrated | 0.184951 | 0.558028 | 0.75162655120503 | 0.048809 | 10692 |
| persistence | 0.350075 | 12.617976 | 0.6027774297442134 | 0.350075 | 10692 |
| hourly_rate | 0.195669 | 0.578159 | 0.6835434016228187 | 0.019936 | 10692 |

## Calibrated model reliability bins

| Range | Count | Mean prediction | Observed rate |
| --- | --- | --- | --- |
| [0.0, 0.1) | 7 | 0.0 | 0.14285714285714285 |
| [0.1, 0.2) | 0 | None | None |
| [0.2, 0.3) | 451 | 0.24761363325430927 | 0.2838137472283814 |
| [0.3, 0.4) | 618 | 0.3163055308820904 | 0.3802588996763754 |
| [0.4, 0.5) | 823 | 0.4518370574206608 | 0.3778857837181045 |
| [0.5, 0.6) | 2240 | 0.551603129106287 | 0.5330357142857143 |
| [0.6, 0.7) | 989 | 0.6163798598329785 | 0.7158746208291203 |
| [0.7, 0.8) | 679 | 0.7752078814831049 | 0.7334315169366715 |
| [0.8, 0.9) | 3405 | 0.8573585397380623 | 0.808223201174743 |
| [0.9, 1.0] | 1480 | 0.9712784052758323 | 0.925 |

## Example inference

```json
{
  "station_id": "S001",
  "eta": "2026-10-18T12:30:00+07:00",
  "p_available": 0.8900083963056253,
  "reasons": [
    "At observation: 2 of 4 ports free.",
    "Calibrated 30-minute ETA prediction (rule-based context, not SHAP).",
    "Training data: simulated; status source: simulated; model source: synthetic-correlated-integration-demo-v1."
  ],
  "explanation_method": "rule",
  "model_version": "lightgbm-a92536a3b5c32ca1",
  "data_type": "simulated",
  "contract_version": "0.1.0"
}
```

Scores describe this synthetic held-out timeline only; do not assume LightGBM wins.
