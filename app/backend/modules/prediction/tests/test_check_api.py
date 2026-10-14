"""HTTP parity rejects placeholders and errors, without live services or keys."""

import httpx
import pytest

from app.backend.modules.prediction.check_api import check_api


@pytest.fixture
def expected_report() -> dict:
    return {
        "passed": True,
        "model_version": "pinned-test-v1",
        "cases": [
            {
                "case_id": "valid_normal_30",
                "request": {
                    "station_id": "S001",
                    "observed_at": "2026-10-13T16:00:00+07:00",
                    "eta": "2026-10-13T16:30:00+07:00",
                    "connector_type": "CCS2",
                    "scenario": "normal",
                },
                "response": {
                    "station_id": "S001",
                    "eta": "2026-10-13T16:30:00+07:00",
                    "p_available": 0.83,
                    "reasons": ["Synthetic test only"],
                    "explanation_method": "rule",
                    "model_version": "pinned-test-v1",
                    "data_type": "simulated",
                    "contract_version": "0.1.0",
                },
            }
        ],
    }


def test_parity_checks_path_request_and_output(expected_report: dict) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/predict"
        assert request.method == "POST"
        return httpx.Response(200, json=expected_report["cases"][0]["response"])

    with httpx.Client(
        base_url="http://test/api/", transport=httpx.MockTransport(handler)
    ) as client:
        result = check_api(client, expected_report)
    assert result["passed"] and result["passed_count"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("p_available", 0.75),
        ("model_version", "fake-v1"),
        ("data_type", "mock"),
        ("eta", "2026-10-13T16:35:00+07:00"),
        ("station_id", "S002"),
    ],
)
def test_parity_rejects_fake_or_wrong_integration(
    expected_report: dict, field: str, value: object
) -> None:
    response = {**expected_report["cases"][0]["response"], field: value}
    with httpx.Client(
        base_url="http://test/api/",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response)),
    ) as client:
        result = check_api(client, expected_report)
    assert not result["passed"] and field in result["cases"][0]["mismatches"]


@pytest.mark.parametrize("status", [422, 503])
def test_non_200_cannot_pass(expected_report: dict, status: int) -> None:
    with httpx.Client(
        base_url="http://test/api/",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(status, json={"detail": "synthetic error"})
        ),
    ) as client:
        assert not check_api(client, expected_report)["passed"]


def test_empty_suite_cannot_pass(expected_report: dict) -> None:
    with httpx.Client(base_url="http://test/api/") as client:
        with pytest.raises(ValueError, match="no valid"):
            check_api(client, {**expected_report, "cases": []})
