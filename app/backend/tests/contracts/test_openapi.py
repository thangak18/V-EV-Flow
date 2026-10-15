import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.backend.api.generate_openapi import generate_document
from app.backend.contracts.prediction import PredictionResult, PredictRequest
from app.backend.contracts.recommendation import RecommendationRequest, RecommendationResult
from app.backend.contracts.simulation import WhatIfRequest, WhatIfResult

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
        ("predict.shap.response.json", PredictionResult),
        ("recommend.shift.response.json", RecommendationResult),
        ("whatif.request.json", WhatIfRequest),
        ("whatif.response.json", WhatIfResult),
    ],
)
def test_examples_validate_against_their_public_models(
    filename: str,
    model: type[BaseModel],
) -> None:
    payload = json.loads((EXAMPLES / filename).read_text())
    model.model_validate(payload)
