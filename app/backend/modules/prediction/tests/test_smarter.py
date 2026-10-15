"""Mock rows verify the public-data benchmark, not measured performance."""

from typing import cast

import numpy as np
import pandas as pd
import pytest

from app.backend.modules.prediction.smarter_data import adapt, features, labels, partition


def fixture():
    times = pd.date_range("2020-07-03", periods=200, freq="15min")
    a = np.arange(len(times)) % 4
    return pd.DataFrame(
        {
            "date": times.astype(str),
            "Station": "A",
            "Available": a,
            "Charging": 3 - a,
            "Passive": 0,
            "Other": 0,
        }
    )


def test_validation_keeps_other_and_rejects_bad_counts():
    raw = fixture()
    raw.loc[0, ["Available", "Charging", "Other"]] = [0, 0, 3]
    frame, audit = adapt(raw)
    assert frame.iloc[0].Other == 3
    assert "ports_broken" not in frame
    assert audit["station_count"] == 1
    for column, value in [("Available", -1), ("Charging", 0.5), ("Other", np.nan)]:
        bad = raw.astype({column: float})
        bad.loc[0, column] = value
        with pytest.raises(ValueError):
            adapt(bad)
    with pytest.raises(ValueError, match="duplicate"):
        adapt(pd.concat([raw, raw.iloc[[0]]]))


def test_exact_future_and_lag_do_not_bridge_missing_ticks():
    raw = fixture().drop(index=1)
    frame, _ = adapt(raw)
    x = features(frame)
    assert np.isnan(x.iloc[1].Available_lag_15)
    target = labels(frame, 15)
    assert 0 not in target.index
    assert target.loc[1, "target"] == int(frame.iloc[2].Available > 0)
    # Change every later snapshot: features at t must remain identical.
    changed = frame.copy()
    changed.loc[1:, ["Available", "Charging"]] = [0, 3]
    pd.testing.assert_series_equal(features(changed).iloc[0], x.iloc[0])


def test_global_embargo_separates_all_future_labels():
    frame, _ = adapt(fixture())
    y = labels(frame, 60)
    parts = partition(
        y,
        cast(pd.Timestamp, pd.Timestamp("2020-07-04")),
        cast(pd.Timestamp, pd.Timestamp("2020-07-04 12:00")),
    )
    assert parts["train"].eta.max() < parts["calibration"].observed_at.min()
    assert parts["calibration"].eta.max() < parts["test"].observed_at.min()
    with pytest.raises(ValueError):
        labels(frame, 5)
    with pytest.raises(ValueError):
        partition(
            y,
            cast(pd.Timestamp, pd.Timestamp("2030-01-01")),
            cast(pd.Timestamp, pd.Timestamp("2031-01-01")),
        )


def test_source_clock_and_dst_are_explicit():
    raw = fixture()
    raw.loc[0, "date"] = "2020-10-25 02:00:00"
    frame, audit = adapt(raw)
    assert audit["dst_day_rows_excluded"] == 1
    assert not frame.date.dt.strftime("%Y-%m-%d").eq("2020-10-25").any()
    raw.loc[0, "date"] = "2020-07-03 00:01:00"
    with pytest.raises(ValueError, match="15-minute"):
        adapt(raw)


def test_end_to_end_artifacts_metrics_and_cli_errors(tmp_path, capsys):
    import json
    import sys
    from unittest.mock import patch

    from app.backend.modules.prediction.smarter_benchmark import main, run

    csv = tmp_path / "mock.csv"
    fixture().to_csv(csv, index=False)
    out = tmp_path / "release"
    report = run(
        csv,
        out,
        cast(pd.Timestamp, pd.Timestamp("2020-07-04")),
        cast(pd.Timestamp, pd.Timestamp("2020-07-04 12:00")),
        estimators=2,
        data_type="mock",
    )
    assert report["data_type"] == "mock"
    assert report["source_url"] is None
    assert report["audit"]["source_rows"] == 200
    with pytest.raises(ValueError, match="checksum mismatch"):
        run(
            csv,
            tmp_path / "wrong-source",
            cast(pd.Timestamp, pd.Timestamp("2020-07-04")),
            cast(pd.Timestamp, pd.Timestamp("2020-07-04 12:00")),
        )
    assert set(report["horizons"]) == {"15", "30", "60"}
    for h, result in report["horizons"].items():
        assert result["calibration_brier"][result["calibration_method"]] == min(
            result["calibration_brier"].values()
        )
        assert set(result["metrics"]) == {
            "lightgbm_raw",
            "lightgbm_calibrated",
            "persistence",
            "hourly_rate",
        }
        probabilities = pd.read_parquet(out / f"predictions-{h}m.parquet")
        assert probabilities.lightgbm_calibrated.between(0, 1).all()
        assert len(result["artifact_sha256"]) == 64
        assert result["metrics"]["lightgbm_calibrated"]["log_loss"] is not None
    assert json.loads((out / "manifest.json").read_text())["embargo_minutes"] == 60
    with pytest.raises(ValueError, match="already contains"):
        run(
            csv,
            out,
            cast(pd.Timestamp, pd.Timestamp("2020-07-04")),
            cast(pd.Timestamp, pd.Timestamp("2020-07-04 12:00")),
            estimators=2,
            data_type="mock",
        )
    args = [
        "benchmark",
        "--csv",
        str(csv),
        "--output",
        str(tmp_path / "bad"),
        "--train-end",
        "NaT",
        "--calibration-end",
        "2020-07-04",
    ]
    with patch.object(sys, "argv", args):
        assert main() == 2
    assert "invalid timestamp" in capsys.readouterr().err


def test_lags_remain_within_station_and_no_fabricated_timezone():
    raw = fixture()
    second = raw.assign(Station="B", Available=0, Charging=0, Passive=3)
    frame, _ = adapt(pd.concat([raw, second]))
    x = features(frame)
    first_b = frame.index[frame.Station == "B"][0]
    assert np.isnan(x.loc[first_b, "Available_lag_15"])
    assert x.loc[first_b + 1, "Available_lag_15"] == 0
    raw["date"] = pd.to_datetime(raw.date).dt.tz_localize("UTC")
    with pytest.raises(ValueError, match="source clock"):
        adapt(raw)
