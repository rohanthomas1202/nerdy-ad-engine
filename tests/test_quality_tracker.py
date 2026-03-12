"""Tests for QualityTracker — per-dimension trends and regression detection."""

from src.analytics.quality_tracker import QualityTracker
from src.models import AdCopy, AdRecord, DimensionScore, EvaluationResult


def _make_record(cycle: int, scores: dict[str, float], status: str = "approved") -> AdRecord:
    """Create an AdRecord with given dimension scores."""
    dim_scores = [
        DimensionScore(dimension=dim, score=score, rationale="Test", confidence=0.9)
        for dim, score in scores.items()
    ]
    aggregate = sum(scores.values()) / len(scores)
    evaluation = EvaluationResult(
        dimension_scores=dim_scores,
        aggregate_score=aggregate,
        passed_quality_gate=aggregate >= 7.0,
        weakest_dimension=min(scores, key=scores.get),
        evaluation_rationale="Test",
    )
    return AdRecord(
        id=f"test-c{cycle}",
        brief_id="test",
        variant_index=0,
        ad_copy=AdCopy(
            primary_text="Test ad copy.",
            headline="Test",
            description="Test desc.",
            cta="Learn More",
        ),
        evaluation=evaluation,
        iteration_history=[evaluation],
        cycle=cycle,
        status=status,
    )


def _default_scores(base: float = 7.0) -> dict[str, float]:
    return {
        "clarity": base + 1.0,
        "value_proposition": base + 0.5,
        "call_to_action": base,
        "brand_voice": base + 0.5,
        "emotional_resonance": base - 0.5,
    }


class TestQualityTracker:
    def test_trend_computation(self):
        """track() should compute per-dimension averages and per-cycle data."""
        tracker = QualityTracker()
        records = [
            _make_record(1, _default_scores(7.0)),
            _make_record(1, _default_scores(7.5)),
            _make_record(2, _default_scores(8.0)),
        ]
        trends = tracker.track(records)
        assert "per_dimension" in trends
        assert "per_cycle" in trends
        assert 1 in trends["per_cycle"]
        assert 2 in trends["per_cycle"]
        assert trends["per_cycle"][2]["avg_score"] > trends["per_cycle"][1]["avg_score"]

    def test_regression_detection_flagged(self):
        """A drop > 0.5 should be flagged as a regression."""
        tracker = QualityTracker()
        records = [
            _make_record(1, {"clarity": 8.0, "emotional_resonance": 7.5}),
            _make_record(2, {"clarity": 8.0, "emotional_resonance": 6.5}),
        ]
        trends = tracker.track(records)
        regressions = tracker.detect_regressions(trends)
        dims = [r["dimension"] for r in regressions]
        assert "emotional_resonance" in dims
        assert regressions[0]["drop"] >= 0.6

    def test_regression_not_flagged_small_drop(self):
        """A drop <= 0.5 should NOT be flagged."""
        tracker = QualityTracker()
        records = [
            _make_record(1, {"clarity": 8.0, "emotional_resonance": 7.5}),
            _make_record(2, {"clarity": 8.0, "emotional_resonance": 7.1}),
        ]
        trends = tracker.track(records)
        regressions = tracker.detect_regressions(trends)
        assert len(regressions) == 0

    def test_single_cycle_no_regression(self):
        """A single cycle should produce no regressions."""
        tracker = QualityTracker()
        records = [_make_record(1, _default_scores(7.0))]
        trends = tracker.track(records)
        regressions = tracker.detect_regressions(trends)
        assert len(regressions) == 0
