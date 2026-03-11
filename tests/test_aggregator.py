"""Tests for Aggregator — weighted scoring and quality gate check."""

import pytest

from src.evaluate.aggregator import Aggregator
from src.models import DimensionScore


class TestAggregator:
    @pytest.fixture
    def aggregator(self):
        return Aggregator()

    def test_uniform_scores_give_expected_aggregate(self, aggregator):
        """If all 5 dimensions score 8.0, aggregate should be 8.0."""
        scores = [
            DimensionScore(dimension="clarity", score=8.0, rationale="Good", confidence=0.9),
            DimensionScore(
                dimension="value_proposition", score=8.0, rationale="Good", confidence=0.9
            ),
            DimensionScore(
                dimension="call_to_action", score=8.0, rationale="Good", confidence=0.9
            ),
            DimensionScore(dimension="brand_voice", score=8.0, rationale="Good", confidence=0.9),
            DimensionScore(
                dimension="emotional_resonance", score=8.0, rationale="Good", confidence=0.9
            ),
        ]
        result = aggregator.aggregate(scores)
        assert result.aggregate_score == 8.0

    def test_weighted_average_is_correct(self, aggregator):
        """Verify weighted average with known different scores."""
        # weights: clarity=0.20, value_prop=0.25, cta=0.20, brand=0.15, emotion=0.20
        scores = [
            DimensionScore(dimension="clarity", score=10.0, rationale="R", confidence=0.9),
            DimensionScore(
                dimension="value_proposition", score=10.0, rationale="R", confidence=0.9
            ),
            DimensionScore(
                dimension="call_to_action", score=10.0, rationale="R", confidence=0.9
            ),
            DimensionScore(dimension="brand_voice", score=10.0, rationale="R", confidence=0.9),
            DimensionScore(
                dimension="emotional_resonance", score=10.0, rationale="R", confidence=0.9
            ),
        ]
        result = aggregator.aggregate(scores)
        assert result.aggregate_score == 10.0

    def test_weakest_dimension_identified(self, aggregator, sample_dimension_scores):
        """Aggregator should correctly identify the lowest-scoring dimension."""
        result = aggregator.aggregate(sample_dimension_scores)
        assert result.weakest_dimension == "emotional_resonance"

    def test_quality_gate_pass_at_threshold(self, aggregator):
        """Score exactly at 7.0 should pass."""
        scores = [
            DimensionScore(dimension="clarity", score=7.0, rationale="R", confidence=0.9),
            DimensionScore(
                dimension="value_proposition", score=7.0, rationale="R", confidence=0.9
            ),
            DimensionScore(
                dimension="call_to_action", score=7.0, rationale="R", confidence=0.9
            ),
            DimensionScore(dimension="brand_voice", score=7.0, rationale="R", confidence=0.9),
            DimensionScore(
                dimension="emotional_resonance", score=7.0, rationale="R", confidence=0.9
            ),
        ]
        result = aggregator.aggregate(scores)
        assert result.passed_quality_gate is True

    def test_quality_gate_fail_below_threshold(self, aggregator):
        """Score below 7.0 should fail."""
        scores = [
            DimensionScore(dimension="clarity", score=6.0, rationale="R", confidence=0.9),
            DimensionScore(
                dimension="value_proposition", score=6.0, rationale="R", confidence=0.9
            ),
            DimensionScore(
                dimension="call_to_action", score=6.0, rationale="R", confidence=0.9
            ),
            DimensionScore(dimension="brand_voice", score=6.0, rationale="R", confidence=0.9),
            DimensionScore(
                dimension="emotional_resonance", score=6.0, rationale="R", confidence=0.9
            ),
        ]
        result = aggregator.aggregate(scores)
        assert result.passed_quality_gate is False
