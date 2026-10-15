"""Reproducible offline public Belib benchmark; never replaces the demo artifact."""

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from app.backend.modules.prediction.metrics import evaluate_probabilities
from app.backend.modules.prediction.smarter_data import HORIZONS, adapt, features, labels, partition


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def logit(values: np.ndarray) -> np.ndarray:
    p = np.clip(values, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p)).reshape(-1, 1)


def calibrated(method: str, model, values: np.ndarray) -> np.ndarray:
    if method == "platt":
        result = model.predict_proba(logit(values))[:, 1]
    else:
        result = model.predict(values)
    return np.clip(np.asarray(result, dtype=float), 0, 1)


def run(
    csv_path: Path,
    output: Path,
    train_end: pd.Timestamp,
    calibration_end: pd.Timestamp,
    *,
    seed: int = 42,
    estimators: int = 120,
    data_type: Literal["real", "mock"] = "real",
) -> dict:
    """Fit each ETA independently with frozen parameters and training-only encodings."""
    if (output / "manifest.json").exists():
        raise ValueError("output already contains a release; choose a new directory")
    input_sha = digest(csv_path)
    # pragma: allowlist nextline secret -- verified public hash
    expected_sha = "0c19fda8d2cb7c83b8df2ddbbc82298f6f0234f69fd387b045cfbb537e071f2a"
    if data_type not in ("real", "mock") or (data_type == "real" and input_sha != expected_sha):
        raise ValueError("published source checksum mismatch; no verified real-data provenance")
    frame, audit = adapt(pd.read_csv(csv_path))
    matrix = features(frame)
    report = {
        "schema_version": "smarter-benchmark-v1",
        "source_url": "https://gitlab.com/smarter-mobility-data-challenge/tutorials",
        # pragma: allowlist nextline secret -- verified public hash
        "upstream_commit": "a431cae1c15887b1fd6ecc43157c48012faced42",
        # pragma: allowlist nextline secret -- verified public hash
        "upstream_train_blob": "8e9cd8ba72bd842325383d567086d60a777734e0",
        "license_reference": "ODbL, as documented by the dataset authors",
        "data_type": data_type,
        "source": "Smarter Mobility / Belib Paris historical aggregates",
        "task": "P(recorded Available > 0 at exact source-clock ETA); station-level only",
        "input_sha256": input_sha,
        "input_bytes": csv_path.stat().st_size,
        "audit": audit,
        "seed": seed,
        "estimators": estimators,
        "train_end": str(train_end),
        "calibration_end": str(calibration_end),
        "embargo_minutes": 60,
        "versions": {
            name: version(name)
            for name in ["pandas", "numpy", "lightgbm", "scikit-learn", "joblib"]
        },
        "python": platform.python_version(),
        "horizons": {},
    }
    if data_type == "mock":
        for key in ("source_url", "upstream_commit", "upstream_train_blob", "license_reference"):
            report[key] = None
        report["source"] = "caller-declared mock fixture"
    output.mkdir(parents=True, exist_ok=True)
    for horizon in HORIZONS:
        print(f"Training {horizon}-minute horizon", file=sys.stderr, flush=True)
        target = labels(frame, horizon)
        splits = partition(target, train_end, calibration_end)
        train, cal, test = (splits[name] for name in ["train", "calibration", "test"])
        if train.target.nunique() != 2 or cal.target.nunique() != 2:
            raise ValueError("training and calibration require both classes")
        station_categories = sorted(train.Station.unique())
        codes = pd.Categorical(frame.Station, categories=station_categories).codes
        x = matrix.assign(station_code=codes)
        model = LGBMClassifier(
            n_estimators=estimators,
            learning_rate=0.05,
            num_leaves=15,
            min_child_samples=50,
            reg_lambda=1.0,
            random_state=seed,
            n_jobs=2,
            deterministic=True,
            force_col_wise=True,
            verbosity=-1,
        )
        model.fit(x.loc[train.index], train.target, categorical_feature=["station_code"])
        cal_p = np.asarray(model.predict_proba(x.loc[cal.index]))[:, 1]
        candidates = {
            "platt": LogisticRegression(C=1.0, random_state=seed).fit(logit(cal_p), cal.target),
            "isotonic": IsotonicRegression(out_of_bounds="clip").fit(cal_p, cal.target),
        }
        cal_scores = {
            name: float(np.mean((calibrated(name, fitted, cal_p) - cal.target) ** 2))
            for name, fitted in candidates.items()
        }
        method = min(cal_scores, key=lambda name: (cal_scores[name], name != "platt"))
        chosen = candidates[method]
        # ETA hour is known at request time. Baseline rates use only train labels.
        rate_frame = train.assign(hour=train.eta.dt.hour)
        hourly = rate_frame.groupby("hour").target.mean()
        global_rate = float(train.target.mean())
        raw = np.asarray(model.predict_proba(x.loc[test.index]))[:, 1]
        predictions = {
            "lightgbm_raw": raw,
            "lightgbm_calibrated": calibrated(method, chosen, raw),
            "persistence": (frame.loc[test.index, "Available"] > 0).to_numpy(dtype=float),
            "hourly_rate": test.eta.dt.hour.map(hourly).fillna(global_rate).to_numpy(dtype=float),
        }
        scores = {
            name: asdict(evaluate_probabilities(test.target, p)) for name, p in predictions.items()
        }
        split_metadata = {
            name: {
                "rows": len(part),
                "observed_start": str(part.observed_at.min()),
                "observed_end": str(part.observed_at.max()),
                "eta_end": str(part.eta.max()),
                "positive_rate": float(part.target.mean()),
            }
            for name, part in splits.items()
        }
        binary = output / f"model-{horizon}m.joblib"
        bundle = {
            "schema_version": report["schema_version"],
            "model": model,
            "calibrator": chosen,
            "calibration_method": method,
            "station_categories": station_categories,
            "feature_columns": list(x.columns),
            "hourly_rate": hourly,
            "global_rate": global_rate,
            "source_timezone": "unspecified",
            "horizon_minutes": horizon,
            "input_sha256": report["input_sha256"],
        }
        joblib.dump(bundle, binary, compress=3)
        restored = joblib.load(binary)  # Trusted, freshly written local artifact only.
        reloaded = calibrated(
            restored["calibration_method"],
            restored["calibrator"],
            np.asarray(restored["model"].predict_proba(x.loc[test.index[:32]]))[:, 1],
        )
        if not np.allclose(reloaded, predictions["lightgbm_calibrated"][:32], rtol=0, atol=1e-12):
            raise ValueError("artifact round-trip probabilities changed")
        for name, part in splits.items():
            part.to_parquet(output / f"{name}-{horizon}m.parquet", index=False)
        test.assign(**predictions).to_parquet(
            output / f"predictions-{horizon}m.parquet", index=False
        )
        report["horizons"][str(horizon)] = {
            "calibration_method": method,
            "calibration_brier": cal_scores,
            "splits": split_metadata,
            "dropped_no_exact_eta": len(frame) - len(target),
            "embargoed_rows": len(target) - sum(len(p) for p in splits.values()),
            "metrics": scores,
            "feature_columns": list(x.columns),
            "artifact": binary.name,
            "artifact_sha256": digest(binary),
            "artifact_roundtrip": "passed, 32 held-out predictions",
        }
    (output / "manifest.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-end", required=True)
    parser.add_argument("--calibration-end", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--estimators", type=int, default=120)
    args = parser.parse_args()
    try:
        if args.estimators < 1:
            raise ValueError("estimators must be positive")
        train_end = pd.Timestamp(args.train_end)
        calibration_end = pd.Timestamp(args.calibration_end)
        if not isinstance(train_end, pd.Timestamp) or not isinstance(calibration_end, pd.Timestamp):
            raise ValueError("invalid timestamp cutoffs")
        report = run(
            args.csv,
            args.output,
            train_end,
            calibration_end,
            seed=args.seed,
            estimators=args.estimators,
        )
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "manifest": str(args.output / "manifest.json"),
                "rows": report["audit"]["source_rows"],
                "horizons": list(report["horizons"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
