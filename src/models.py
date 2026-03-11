"""Pydantic data models — the contract layer for the entire system."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_CTAS = ["Learn More", "Sign Up", "Get Started", "Book Now", "Try Free"]


class AdCopy(BaseModel):
    """Generated ad copy with format constraints."""

    primary_text: str = Field(..., max_length=500, description="Main body copy (max 500 chars)")
    headline: str = Field(..., max_length=40, description="Bold headline (max 40 chars)")
    description: str = Field(..., max_length=125, description="Secondary text (max 125 chars)")
    cta: str = Field(..., description="Call-to-action button label")

    @field_validator("cta")
    @classmethod
    def cta_must_be_allowed(cls, v: str) -> str:
        if v not in ALLOWED_CTAS:
            raise ValueError(f"CTA must be one of {ALLOWED_CTAS}, got '{v}'")
        return v


class Brief(BaseModel):
    """Ad brief — input to the generation pipeline."""

    id: str
    audience_segment: str
    product: str
    campaign_goal: Literal["awareness", "conversion"]
    tone_override: str | None = None
    key_message: str | None = None
    enrichment_context: str | None = None


class DimensionScore(BaseModel):
    """Score for a single evaluation dimension."""

    dimension: str
    score: float = Field(..., ge=1.0, le=10.0, description="Score from 1.0 to 10.0")
    rationale: str = Field(..., min_length=1, description="Explanation for the score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level 0.0 to 1.0")


class EvaluationResult(BaseModel):
    """Aggregated evaluation across all dimensions."""

    dimension_scores: list[DimensionScore]
    aggregate_score: float
    passed_quality_gate: bool
    weakest_dimension: str
    evaluation_rationale: str


class AdRecord(BaseModel):
    """Complete record for a generated ad through the pipeline."""

    id: str
    brief_id: str
    variant_index: int
    ad_copy: AdCopy
    evaluation: EvaluationResult | None = None
    iteration_history: list[EvaluationResult] = Field(default_factory=list)
    status: Literal["draft", "approved", "failed"] = "draft"
    generation_cost_usd: float = 0.0
    evaluation_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_used: str = ""


class Diagnosis(BaseModel):
    """Dimension-level weakness diagnosis for targeted editing."""

    weakest_dimension: str
    score: float
    problem_description: str
    suggested_fix: str
    preserve_dimensions: list[str] = Field(
        default_factory=list,
        description="Dimensions scoring well that must not regress",
    )


class LLMUsage(BaseModel):
    """Token and cost tracking for a single LLM call."""

    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    call_type: str  # generation, evaluation, editing, research, calibration
    duration_seconds: float = 0.0


class CalibrationResult(BaseModel):
    """Result of evaluating a single reference ad during calibration."""

    reference_ad_id: str
    expected_tier: str  # high, medium, low
    actual_scores: list[DimensionScore]
    aggregate_score: float
    alignment: Literal["aligned", "misaligned"]


class ExperimentEntry(BaseModel):
    """Structured experiment log entry."""

    id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hypothesis: str
    change: str
    result: str
    metrics_before: dict = Field(default_factory=dict)
    metrics_after: dict = Field(default_factory=dict)
