"""Tests for QualityGate — routing based on score threshold."""


from src.evaluate.quality_gate import QualityGate
from src.models import DimensionScore, EvaluationResult


def _make_evaluation(aggregate: float) -> EvaluationResult:
    """Helper to create an EvaluationResult with a given aggregate score."""
    return EvaluationResult(
        dimension_scores=[
            DimensionScore(
                dimension="clarity", score=aggregate, rationale="Test", confidence=0.9
            )
        ],
        aggregate_score=aggregate,
        passed_quality_gate=aggregate >= 7.0,
        weakest_dimension="clarity",
        evaluation_rationale="Test",
    )


class TestQualityGate:
    def test_approved_when_above_threshold(self):
        gate = QualityGate(threshold=7.0)
        result = gate.check(_make_evaluation(7.5))
        assert result == "approved"

    def test_approved_at_exactly_threshold(self):
        gate = QualityGate(threshold=7.0)
        result = gate.check(_make_evaluation(7.0))
        assert result == "approved"

    def test_needs_editing_below_threshold(self):
        gate = QualityGate(threshold=7.0)
        result = gate.check(_make_evaluation(6.5), attempt=0)
        assert result == "needs_editing"

    def test_failed_after_max_attempts(self):
        gate = QualityGate(threshold=7.0)
        result = gate.check(_make_evaluation(6.5), attempt=3)
        assert result == "failed"

    def test_custom_threshold(self):
        gate = QualityGate(threshold=8.0)
        assert gate.check(_make_evaluation(7.5)) == "needs_editing"
        assert gate.check(_make_evaluation(8.0)) == "approved"
        assert gate.threshold == 8.0
