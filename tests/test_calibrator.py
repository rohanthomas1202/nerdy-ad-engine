"""Tests for Calibrator — evaluator validation against reference ads."""

import json
from unittest.mock import MagicMock

import pytest

from src.evaluate.aggregator import Aggregator
from src.evaluate.calibrator import Calibrator
from src.evaluate.dimension_scorer import DimensionScorer
from src.models import LLMUsage


def _make_scores_json(score_val: float) -> str:
    """Create a mock LLM response with all dimensions at a given score."""
    return json.dumps(
        {
            "scores": [
                {
                    "dimension": dim,
                    "score": score_val,
                    "rationale": f"Score {score_val}",
                    "confidence": 0.85,
                }
                for dim in [
                    "clarity",
                    "value_proposition",
                    "call_to_action",
                    "brand_voice",
                    "emotional_resonance",
                ]
            ]
        }
    )


@pytest.fixture
def mock_scorer_by_tier():
    """Mock scorer that returns high scores for 'high' ads and low for 'low' ads."""
    # We need to intercept based on the ad content, but since we mock the client,
    # we'll set up a sequence of returns based on the reference_ads.json order

    mock_usage = LLMUsage(
        model="gemini-2.0-pro",
        input_tokens=100,
        output_tokens=100,
        cost_usd=0.001,
        call_type="calibration",
    )

    # Reference ads order: high, high, high, high, medium, medium, medium, low, low, low, low
    score_map = {
        "high": 8.0,
        "medium": 6.0,
        "low": 3.0,
    }

    # Read reference ads to build return sequence
    with open("data/reference_ads.json") as f:
        ref_ads = json.load(f)

    responses = []
    for ad in ref_ads:
        tier = ad["performance_tier"]
        responses.append((_make_scores_json(score_map[tier]), mock_usage))

    client = MagicMock()
    client.generate.side_effect = responses

    scorer = DimensionScorer(client=client)
    return scorer


class TestCalibrator:
    def test_high_tier_ads_aligned(self, mock_scorer_by_tier):
        """High-tier reference ads should be scored as aligned."""
        aggregator = Aggregator()
        calibrator = Calibrator(mock_scorer_by_tier, aggregator)
        results = calibrator.run_calibration()

        high_results = [r for r in results if r.expected_tier == "high"]
        for r in high_results:
            assert r.alignment == "aligned", f"{r.reference_ad_id} should be aligned"

    def test_low_tier_ads_aligned(self, mock_scorer_by_tier):
        """Low-tier reference ads should be scored as aligned."""
        aggregator = Aggregator()
        calibrator = Calibrator(mock_scorer_by_tier, aggregator)
        results = calibrator.run_calibration()

        low_results = [r for r in results if r.expected_tier == "low"]
        for r in low_results:
            assert r.alignment == "aligned", f"{r.reference_ad_id} should be aligned"

    def test_report_alignment_rate(self, mock_scorer_by_tier):
        """Report should compute correct alignment rate."""
        aggregator = Aggregator()
        calibrator = Calibrator(mock_scorer_by_tier, aggregator)
        results = calibrator.run_calibration()
        report = calibrator.report(results)

        assert report["alignment_rate"] == 1.0  # all should align with our mocks
        assert report["rank_order_correct"] is True
        assert report["avg_score_by_tier"]["high"] > report["avg_score_by_tier"]["low"]

    def test_report_structure(self, mock_scorer_by_tier):
        """Report should contain all expected fields."""
        aggregator = Aggregator()
        calibrator = Calibrator(mock_scorer_by_tier, aggregator)
        results = calibrator.run_calibration()
        report = calibrator.report(results)

        assert "total_ads" in report
        assert "aligned" in report
        assert "misaligned" in report
        assert "alignment_rate" in report
        assert "avg_score_by_tier" in report
        assert "rank_order_correct" in report
