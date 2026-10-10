import json
from pathlib import Path

import pytest

from app.backend.contracts.generate_openapi import generate_document
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import RecommendationRequest, RecommendationResult

EXAMPLES = Path("app/backend/contracts/examples")


def test_committed_openapi_matches_generated_document() -> None:
    assert Path("app/backend/contracts/openapi.yaml").read_text() == generate_document()


@pytest.mark.parametrize(
    ("filename", "model"),
    [
        ("predict.request.json", PredictRequest),
        ("predict.response.json", PredictionResult),
        ("recommend.request.json", RecommendationRequest),
        ("recommend.response.json", RecommendationResult),
    ],
)
def test_examples_validate_against_their_public_models(
    filename: str,
    model: type[PredictRequest | PredictionResult | RecommendationRequest | RecommendationResult],
) -> None:
    payload = json.loads((EXAMPLES / filename).read_text())
    model.model_validate(payload)
