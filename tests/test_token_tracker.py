"""Tests for TokenTracker — cost analytics and quality-per-dollar."""

from src.analytics.token_tracker import TokenTracker
from src.models import AdCopy, AdRecord, DimensionScore, EvaluationResult, LLMUsage


def _make_usage(call_type: str, cost: float, model: str = "gemini-2.5-pro") -> LLMUsage:
    return LLMUsage(
        model=model, input_tokens=500, output_tokens=200,
        cost_usd=cost, call_type=call_type,
    )


def _make_record(status: str = "approved", score: float = 7.5) -> AdRecord:
    dim_scores = [
        DimensionScore(dimension="clarity", score=score, rationale="Test", confidence=0.9),
    ]
    evaluation = EvaluationResult(
        dimension_scores=dim_scores,
        aggregate_score=score,
        passed_quality_gate=score >= 7.0,
        weakest_dimension="clarity",
        evaluation_rationale="Test",
    )
    return AdRecord(
        id="test",
        brief_id="test",
        variant_index=0,
        ad_copy=AdCopy(
            primary_text="Test.", headline="T", description="D.", cta="Learn More",
        ),
        evaluation=evaluation,
        status=status,
    )


class TestTokenTracker:
    def test_cost_aggregation(self):
        """summarize() should total costs correctly."""
        tracker = TokenTracker()
        usage_log = [
            _make_usage("generation", 0.001),
            _make_usage("evaluation", 0.003),
            _make_usage("editing", 0.002),
        ]
        records = [_make_record()]
        summary = tracker.summarize(records, usage_log)
        assert summary["total_cost"] == 0.006

    def test_cost_per_ad(self):
        """cost_per_ad should be total_cost / num_ads."""
        tracker = TokenTracker()
        usage_log = [_make_usage("generation", 0.01)]
        records = [_make_record(), _make_record()]
        summary = tracker.summarize(records, usage_log)
        assert summary["cost_per_ad"] == 0.005

    def test_quality_per_dollar(self):
        """quality_per_dollar = avg_score / cost_per_ad."""
        tracker = TokenTracker()
        usage_log = [_make_usage("generation", 0.01)]
        records = [_make_record(score=8.0)]
        summary = tracker.summarize(records, usage_log)
        assert summary["quality_per_dollar"] > 0
        assert summary["avg_score"] == 8.0

    def test_empty_log(self):
        """summarize() should handle empty inputs gracefully."""
        tracker = TokenTracker()
        summary = tracker.summarize([], [])
        assert summary["total_cost"] == 0.0
        assert summary["cost_per_ad"] == 0.0
        assert summary["quality_per_dollar"] == 0.0
