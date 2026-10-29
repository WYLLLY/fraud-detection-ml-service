"""Closed HTTP contracts for experimental synthetic-risk inference."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScoreRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)
    amount_minor: int = Field(ge=1, le=10**12)
    currency: Literal["EUR", "USD", "JPY"]


class ScoreResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)
    score: float = Field(ge=0, le=1)
    recommendation: Literal["low_synthetic_risk", "elevated_synthetic_risk"]
    model_version: str = Field(pattern=r"^[a-f0-9]{64}$")
    feature_schema_version: Literal["synthetic-risk-v1"] = "synthetic-risk-v1"
    experimental: Literal[True] = True
    training_data: Literal["synthetic"] = "synthetic"
