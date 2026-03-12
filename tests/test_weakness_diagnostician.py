"""Tests for WeaknessDiagnostician — dimension-level diagnosis."""

import json
from unittest.mock import MagicMock

from src.iterate.weakness_diagnostician import WeaknessDiagnostician
from src.models import DimensionScore, EvaluationResult, LLMUsage


def _make_mock_diagnostician():
    """Create a WeaknessDiagnostician with mocked LLM."""
    mock_client = MagicMock()
    diagnosis_json = json.dumps({
        "problem_description": (
            "The primary text relies entirely on rational arguments "
            "about score improvement without any emotional connection."
        ),
        "suggested_fix": (
            "Add a parent-perspective opening that acknowledges the "
            "stress of watching your child struggle with standardized tests."
        ),
    })
    mock_usage = LLMUsage(
        model="gemini-2.5-pro", input_tokens=600, output_tokens=150,
        cost_usd=0.003, call_type="editing",
    )
    mock_client.generate.return_value = (diagnosis_json, mock_usage)
    return WeaknessDiagnostician(mock_client), mock_client


def _make_eval_with_weak_dimension(weak_dim="emotional_resonance", weak_score=5.5):
    """Create an EvaluationResult with a specific weak dimension."""
    scores = [
        DimensionScore(
            dimension="clarity", score=8.0,
            rationale="Clear", confidence=0.9,
        ),
        DimensionScore(
            dimension="value_proposition", score=7.5,
            rationale="Good", confidence=0.85,
        ),
        DimensionScore(
            dimension="call_to_action", score=7.0,
            rationale="OK", confidence=0.8,
        ),
        DimensionScore(
            dimension="brand_voice", score=8.5,
            rationale="On-brand", confidence=0.9,
        ),
        DimensionScore(
            dimension="emotional_resonance", score=6.5,
            rationale="Weak", confidence=0.75,
        ),
    ]
    # Override the weak dimension score
    for s in scores:
        if s.dimension == weak_dim:
            s.score = weak_score
            s.rationale = "Needs improvement"
    return EvaluationResult(
        dimension_scores=scores,
        aggregate_score=6.5,
        passed_quality_gate=False,
        weakest_dimension=weak_dim,
        evaluation_rationale="Below threshold.",
    )


class TestWeaknessDiagnostician:
    def test_diagnose_returns_correct_weakest_dimension(self, sample_ad_copy):
        """Diagnosis should target the weakest dimension from evaluation."""
        diag, _ = _make_mock_diagnostician()
        evaluation = _make_eval_with_weak_dimension("emotional_resonance", 5.5)
        diagnosis, usage = diag.diagnose(sample_ad_copy, evaluation)
        assert diagnosis.weakest_dimension == "emotional_resonance"

    def test_diagnose_has_specific_problem_description(self, sample_ad_copy):
        """Problem description should be non-empty and specific."""
        diag, _ = _make_mock_diagnostician()
        evaluation = _make_eval_with_weak_dimension()
        diagnosis, _ = diag.diagnose(sample_ad_copy, evaluation)
        assert len(diagnosis.problem_description) > 20
        assert "rational" in diagnosis.problem_description.lower()

    def test_diagnose_has_specific_suggested_fix(self, sample_ad_copy):
        """Suggested fix should be non-empty and actionable."""
        diag, _ = _make_mock_diagnostician()
        evaluation = _make_eval_with_weak_dimension()
        diagnosis, _ = diag.diagnose(sample_ad_copy, evaluation)
        assert len(diagnosis.suggested_fix) > 20
        assert "parent" in diagnosis.suggested_fix.lower()

    def test_preserve_dimensions_lists_strong_ones(self, sample_ad_copy):
        """Preserve list should include dimensions scoring >= 7.0."""
        diag, _ = _make_mock_diagnostician()
        evaluation = _make_eval_with_weak_dimension("emotional_resonance", 5.5)
        diagnosis, _ = diag.diagnose(sample_ad_copy, evaluation)
        assert "clarity" in diagnosis.preserve_dimensions
        assert "brand_voice" in diagnosis.preserve_dimensions
        assert "emotional_resonance" not in diagnosis.preserve_dimensions
