from math import exp

import pytest
from pydantic import ValidationError

from app.backend.contracts.explanations import ModelExplanation
from app.backend.contracts.simulation import WhatIfRequest


def test_shap_requires_raw_margin_additivity_and_distinguishes_calibration() -> None:
    payload = dict(
        bias=0.1,
        raw_score=0.5,
        raw_probability=1 / (1 + exp(-0.5)),
        calibrated_probability=0.8,
        features=[dict(feature="ports_free", value=2, contribution=0.4)],
    )
    explanation = ModelExplanation.model_validate(payload)
    assert explanation.space == "raw_margin_log_odds"
    with pytest.raises(ValidationError, match="reconstruct"):
        ModelExplanation.model_validate(payload | {"raw_score": 1.0})
    with pytest.raises(ValidationError, match="sigmoid"):
        ModelExplanation.model_validate(payload | {"raw_probability": 0.2})


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "add_ports", "station_id": "S001", "ports": 0},
        {"kind": "shift_departures", "fraction": 0.2, "target_hour": 23},
        {"kind": "add_ports", "station_id": "S001", "ports": 2, "secret": "not allowed"},
    ],
)
def test_counterfactual_units_and_shapes_are_explicit(change: dict) -> None:
    with pytest.raises(ValidationError):
        WhatIfRequest.model_validate(
            dict(
                scenario="normal",
                seed=42,
                vehicle_count=100,
                strategy="ai_allocation",
                change=change,
            )
        )


def test_offpeak_requires_at_least_one_shifted_vehicle() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        WhatIfRequest.model_validate(
            dict(
                scenario="normal",
                seed=42,
                vehicle_count=1,
                strategy="ai_allocation",
                change={"kind": "shift_departures", "fraction": 0.2, "target_hour": 21},
            )
        )
