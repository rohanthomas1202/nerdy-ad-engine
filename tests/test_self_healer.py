"""Tests for SelfHealer — regression diagnosis and fix suggestions."""

import json
from unittest.mock import MagicMock

from src.analytics.self_healer import SelfHealer
from src.models import AdCopy, AdRecord, DimensionScore, EvaluationResult, LLMUsage


def _make_mock_healer():
    """Create a SelfHealer with mocked LLM."""
    mock_client = MagicMock()
    diagnosis_response = json.dumps({
        "diagnosis": (
            "Recent ads lack parent-perspective emotional hooks. "
            "The primary text uses only rational arguments."
        ),
        "suggested_fix": (
            "Add parent empathy opening that acknowledges test stress "
            "before presenting the value proposition."
        ),
    })
    mock_usage = LLMUsage(
        model="gemini-2.5-pro", input_tokens=600, output_tokens=150,
        cost_usd=0.003, call_type="self_healing",
    )
    mock_client.generate.return_value = (diagnosis_response, mock_usage)
    return SelfHealer(mock_client), mock_client


def _make_poor_record():
    dim_scores = [
        DimensionScore(
            dimension="emotional_resonance", score=5.5,
            rationale="Weak emotion", confidence=0.8,
        ),
        DimensionScore(
            dimension="clarity", score=8.0,
            rationale="Clear", confidence=0.9,
        ),
    ]
    return AdRecord(
        id="test-poor",
        brief_id="test",
        variant_index=0,
        ad_copy=AdCopy(
            primary_text="Our tutors help students improve SAT scores.",
            headline="SAT Prep",
            description="Expert tutoring available.",
            cta="Learn More",
        ),
        evaluation=EvaluationResult(
            dimension_scores=dim_scores,
            aggregate_score=6.5,
            passed_quality_gate=False,
            weakest_dimension="emotional_resonance",
            evaluation_rationale="Below threshold.",
        ),
        status="failed",
    )


class TestSelfHealer:
    def test_diagnose_regression_returns_text(self):
        """diagnose_regression() should return diagnosis text and usage."""
        healer, _ = _make_mock_healer()
        regression = {
            "dimension": "emotional_resonance",
            "previous_avg": 7.5,
            "current_avg": 6.5,
            "drop": 1.0,
        }
        text, usage = healer.diagnose_regression(regression, [_make_poor_record()])
        assert len(text) > 0
        assert usage.call_type == "self_healing"

    def test_heal_returns_non_empty_results(self):
        """heal() should return a result for each regression."""
        healer, _ = _make_mock_healer()
        regressions = [{
            "dimension": "emotional_resonance",
            "previous_avg": 7.5,
            "current_avg": 6.5,
            "drop": 1.0,
        }]
        results = healer.heal(regressions, [_make_poor_record()])
        assert len(results) == 1
        assert results[0]["dimension"] == "emotional_resonance"
        assert len(results[0]["diagnosis"]) > 0

    def test_suggest_fix_is_actionable(self):
        """suggest_fix() should extract actionable suggestion from JSON."""
        healer, _ = _make_mock_healer()
        diagnosis_json = json.dumps({
            "diagnosis": "Ads lack emotion.",
            "suggested_fix": "Add parent empathy opening.",
        })
        fix = healer.suggest_fix(diagnosis_json)
        assert "empathy" in fix.lower()
