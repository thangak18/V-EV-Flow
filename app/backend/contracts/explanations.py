"""Optional model explanations in raw-margin space, never probability contributions."""

from math import exp, isclose
from typing import Literal

from pydantic import Field, model_validator

from .common import StrictModel


class FeatureContribution(StrictModel):
    feature: str = Field(min_length=1)
    value: float = Field(allow_inf_nan=False)
    contribution: float = Field(allow_inf_nan=False)


class ModelExplanation(StrictModel):
    method: Literal["tree_shap"] = "tree_shap"
    space: Literal["raw_margin_log_odds"] = "raw_margin_log_odds"
    bias: float = Field(allow_inf_nan=False)
    raw_score: float = Field(allow_inf_nan=False)
    raw_probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    calibrated_probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    features: tuple[FeatureContribution, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def contributions_reconstruct_margin(self) -> "ModelExplanation":
        if len({item.feature for item in self.features}) != len(self.features):
            raise ValueError("explanation feature names must be unique")
        if not isclose(
            self.bias + sum(item.contribution for item in self.features),
            self.raw_score,
            rel_tol=1e-6,
            abs_tol=1e-6,
        ):
            raise ValueError("SHAP contributions must reconstruct the raw margin")
        expected = (
            1 / (1 + exp(-self.raw_score))
            if self.raw_score >= 0
            else exp(self.raw_score) / (1 + exp(self.raw_score))
        )
        if not isclose(self.raw_probability, expected, rel_tol=1e-7, abs_tol=1e-7):
            raise ValueError("raw probability must be the sigmoid of the raw margin")
        return self
