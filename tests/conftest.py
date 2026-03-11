"""Shared pytest fixtures for the Nerdy Ad Engine test suite."""

import json
from unittest.mock import MagicMock

import pytest

from src.models import AdCopy, Brief, DimensionScore, EvaluationResult, LLMUsage


@pytest.fixture
def sample_ad_copy():
    """A realistic Varsity Tutors ad."""
    return AdCopy(
        primary_text=(
            "Your SAT score can improve 200+ points. Our expert tutors create a "
            "personalized plan that targets your weak areas. No cookie-cutter programs. "
            "Just 1-on-1 support designed around how you learn best."
        ),
        headline="Boost Your SAT Score 200+ Pts",
        description="Personalized 1-on-1 SAT tutoring. Free first session, no commitment.",
        cta="Try Free",
    )


@pytest.fixture
def sample_brief():
    """A standard SAT prep brief."""
    return Brief(
        id="test-brief-01",
        audience_segment="parents_anxious",
        product="SAT Test Prep",
        campaign_goal="conversion",
        key_message="Raise your SAT score 200+ points with personalized tutoring",
    )


@pytest.fixture
def sample_dimension_scores():
    """5 sample dimension scores."""
    return [
        DimensionScore(dimension="clarity", score=8.0, rationale="Clear message", confidence=0.9),
        DimensionScore(
            dimension="value_proposition", score=7.5, rationale="Good specifics", confidence=0.85
        ),
        DimensionScore(
            dimension="call_to_action", score=7.0, rationale="Clear CTA", confidence=0.8
        ),
        DimensionScore(
            dimension="brand_voice", score=8.5, rationale="On-brand tone", confidence=0.9
        ),
        DimensionScore(
            dimension="emotional_resonance", score=6.5, rationale="Some emotion", confidence=0.75
        ),
    ]


@pytest.fixture
def sample_evaluation_result(sample_dimension_scores):
    """A pre-built evaluation result."""
    return EvaluationResult(
        dimension_scores=sample_dimension_scores,
        aggregate_score=7.45,
        passed_quality_gate=True,
        weakest_dimension="emotional_resonance",
        evaluation_rationale="Aggregate: 7.45 (PASS).",
    )


@pytest.fixture
def mock_llm_scores_json():
    """JSON string that the LLM would return for scoring."""
    return json.dumps(
        {
            "scores": [
                {
                    "dimension": "clarity",
                    "score": 8.0,
                    "rationale": "Message is clear and easy to understand.",
                    "confidence": 0.9,
                },
                {
                    "dimension": "value_proposition",
                    "score": 7.5,
                    "rationale": "Specific claims with good differentiation.",
                    "confidence": 0.85,
                },
                {
                    "dimension": "call_to_action",
                    "score": 7.0,
                    "rationale": "Clear next step with low friction.",
                    "confidence": 0.8,
                },
                {
                    "dimension": "brand_voice",
                    "score": 8.5,
                    "rationale": "Empowering and approachable tone.",
                    "confidence": 0.9,
                },
                {
                    "dimension": "emotional_resonance",
                    "score": 6.5,
                    "rationale": "Some emotional connection but could be deeper.",
                    "confidence": 0.75,
                },
            ]
        }
    )


@pytest.fixture
def mock_llm_usage():
    """A sample LLMUsage object."""
    return LLMUsage(
        model="gemini-2.0-pro",
        input_tokens=500,
        output_tokens=200,
        cost_usd=0.001625,
        call_type="evaluation",
        duration_seconds=1.5,
    )


@pytest.fixture
def mock_gemini_client(mock_llm_scores_json, mock_llm_usage):
    """A mocked GeminiClient that returns predetermined responses."""
    client = MagicMock()
    client.generate.return_value = (mock_llm_scores_json, mock_llm_usage)
    client._usage_log = [mock_llm_usage]
    client.total_cost = mock_llm_usage.cost_usd
    client.usage_log = [mock_llm_usage]
    return client
