"""Black-box acceptance check for an API that should use the pinned Predictor.

This local verification tool does not implement API wiring or change requests.
A fake predictor is a mismatch, never accepted as a successful model handoff.
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import httpx

from app.backend.contracts.prediction import PredictionResult, PredictRequest


def check_api(client: httpx.Client, expected_report: dict[str, Any]) -> dict[str, Any]:
    """Compare valid acceptance requests with actual HTTP prediction responses."""
    if expected_report.get("passed") is not True:
        raise ValueError("expected report must have passed local inference acceptance")
    valid = [c for c in expected_report.get("cases", []) if c["case_id"].startswith("valid_")]
    if not valid:
        raise ValueError("expected report has no valid inference cases")
    records = []
    for case in valid:
        request = PredictRequest.model_validate(case["request"])
        expected = PredictionResult.model_validate(case["response"])
        if expected.model_version != expected_report["model_version"]:
            raise ValueError("expected report mixes model versions")
        record: dict[str, Any] = {"case_id": case["case_id"], "passed": False}
        try:
            response = client.post("predict", json=request.model_dump(mode="json"))
            record["http_status"] = response.status_code
            if response.status_code != 200:
                record["mismatch"] = "prediction did not return HTTP 200"
            else:
                actual = PredictionResult.model_validate(response.json())
                record["response"] = actual.model_dump(mode="json")
                mismatches = [
                    name
                    for name in (
                        "station_id",
                        "eta",
                        "model_version",
                        "data_type",
                        "contract_version",
                    )
                    if getattr(actual, name) != getattr(expected, name)
                ]
                if not math.isclose(
                    actual.p_available, expected.p_available, rel_tol=0, abs_tol=1e-8
                ):
                    mismatches.append("p_available")
                record["mismatches"] = mismatches
                record["passed"] = not mismatches
        except (httpx.HTTPError, ValueError) as exc:
            record["error_type"] = type(exc).__name__
            record["mismatch"] = "transport failure or invalid prediction payload"
        records.append(record)
    return {
        "model_version": expected_report["model_version"],
        "case_count": len(records),
        "passed_count": sum(r["passed"] for r in records),
        "passed": all(r["passed"] for r in records),
        "scope": "HTTP /predict parity only; does not verify recommendation or UI integration",
        "cases": records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base-url", required=True, help="e.g. http://127.0.0.1:8000/api/")
    parser.add_argument("--expected-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.resolve() == args.expected_report.resolve():
            raise ValueError("output must not overwrite expected report")
        expected = json.loads(args.expected_report.read_text())
        with httpx.Client(base_url=args.api_base_url.rstrip("/") + "/", timeout=10) as client:
            result = check_api(client, expected)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"HTTP parity setup failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"{result['passed_count']}/{result['case_count']} HTTP predictions match pinned artifact")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
