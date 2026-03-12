"""Tests for ReferenceAnalyzer — performance correlation analysis."""

import json
from unittest.mock import MagicMock

from src.models import LLMUsage
from src.research.reference_analyzer import ReferenceAnalyzer


def _make_mock_ref_analyzer():
    """Create a ReferenceAnalyzer with mocked LLM."""
    mock_client = MagicMock()

    ref_response = json.dumps({
        "winning_patterns": [
            {
                "pattern": "Parent empathy opening",
                "description": "High-performing ads open with parent-perspective emotional hook",
                "examples": ["You've watched your child stress over practice tests"],
            },
            {
                "pattern": "Specific score claims",
                "description": "Concrete numbers (200+ points) build credibility",
                "examples": ["improve their SAT scores by an average of 200+ points"],
            },
        ],
        "losing_patterns": [
            {
                "pattern": "Corporate jargon",
                "description": "Buzzwords like 'synergistically' destroy readability",
            },
            {
                "pattern": "Fear-mongering",
                "description": "Pressure tactics are off-brand and reduce trust",
            },
        ],
        "structural_insights": [
            "High-performing ads use 2-3 short sentences before the value proposition",
            "Best ads end with a specific, low-friction CTA like 'Free first session'",
        ],
        "emotional_insights": [
            "Top ads address parent anxiety directly before offering the solution",
            "Low-performing ads either ignore emotion or use fear-based tactics",
        ],
    })
    mock_usage = LLMUsage(
        model="gemini-2.5-pro", input_tokens=800, output_tokens=300,
        cost_usd=0.005, call_type="research",
    )
    mock_client.generate.return_value = (ref_response, mock_usage)

    # Use the real reference_ads.json
    return ReferenceAnalyzer(mock_client), mock_client


class TestReferenceAnalyzer:
    def test_analyze_returns_correlations(self):
        """analyze_performance_correlations() should return a dict with patterns."""
        analyzer, _ = _make_mock_ref_analyzer()
        correlations, usage = analyzer.analyze_performance_correlations()
        assert "winning_patterns" in correlations
        assert "losing_patterns" in correlations
        assert usage.call_type == "research"

    def test_tier_separation(self):
        """Results should include distinct winning and losing patterns."""
        analyzer, _ = _make_mock_ref_analyzer()
        correlations, _ = analyzer.analyze_performance_correlations()
        assert len(correlations["winning_patterns"]) >= 1
        assert len(correlations["losing_patterns"]) >= 1
        # Winning and losing should be different
        win_names = {p["pattern"] for p in correlations["winning_patterns"]}
        lose_names = {p["pattern"] for p in correlations["losing_patterns"]}
        assert win_names.isdisjoint(lose_names)

    def test_patterns_include_structural_insights(self):
        """Results should include hooks, angles, and structural insights."""
        analyzer, _ = _make_mock_ref_analyzer()
        correlations, _ = analyzer.analyze_performance_correlations()
        assert "structural_insights" in correlations
        assert len(correlations["structural_insights"]) >= 1
        assert "emotional_insights" in correlations
