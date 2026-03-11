"""Tests for DimensionScorer — the most critical module."""

import json
from unittest.mock import MagicMock

import pytest

from src.evaluate.dimension_scorer import DimensionScorer
from src.models import LLMUsage


class TestDimensionScorer:
    def test_score_returns_five_dimensions(
        self, sample_ad_copy, mock_gemini_client, mock_llm_scores_json, mock_llm_usage
    ):
        """Scorer should return exactly 5 DimensionScore objects."""
        scorer = DimensionScorer(client=mock_gemini_client)
        scores, usage = scorer.score(sample_ad_copy)

        assert len(scores) == 5
        dims = {s.dimension for s in scores}
        assert dims == {
            "clarity",
            "value_proposition",
            "call_to_action",
            "brand_voice",
            "emotional_resonance",
        }

    def test_scores_have_non_empty_rationales(
        self, sample_ad_copy, mock_gemini_client
    ):
        """Each score should have a non-empty rationale."""
        scorer = DimensionScorer(client=mock_gemini_client)
        scores, _ = scorer.score(sample_ad_copy)

        for s in scores:
            assert len(s.rationale) > 0

    def test_scores_within_valid_range(
        self, sample_ad_copy, mock_gemini_client
    ):
        """All scores must be between 1.0 and 10.0."""
        scorer = DimensionScorer(client=mock_gemini_client)
        scores, _ = scorer.score(sample_ad_copy)

        for s in scores:
            assert 1.0 <= s.score <= 10.0
            assert 0.0 <= s.confidence <= 1.0

    def test_missing_dimension_raises_error(self, sample_ad_copy):
        """If LLM returns fewer than 5 dimensions, raise ValueError."""
        incomplete_json = json.dumps(
            {
                "scores": [
                    {
                        "dimension": "clarity",
                        "score": 8.0,
                        "rationale": "Clear",
                        "confidence": 0.9,
                    },
                    {
                        "dimension": "value_proposition",
                        "score": 7.0,
                        "rationale": "Good",
                        "confidence": 0.8,
                    },
                ]
            }
        )
        mock_usage = LLMUsage(
            model="gemini-2.0-pro",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            call_type="evaluation",
        )
        client = MagicMock()
        client.generate.return_value = (incomplete_json, mock_usage)

        scorer = DimensionScorer(client=client)
        with pytest.raises(ValueError, match="Missing dimension scores"):
            scorer.score(sample_ad_copy)

    def test_uses_pro_model(self, sample_ad_copy, mock_gemini_client):
        """Evaluation should use Gemini Pro, not Flash."""
        scorer = DimensionScorer(client=mock_gemini_client)
        scorer.score(sample_ad_copy)

        call_args = mock_gemini_client.generate.call_args
        assert call_args.kwargs.get("model_type") == "pro" or (
            len(call_args.args) >= 2 and call_args.args[1] == "pro"
        )
