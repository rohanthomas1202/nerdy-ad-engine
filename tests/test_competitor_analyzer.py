"""Tests for CompetitorAnalyzer — structural pattern extraction from competitor ads."""

import json
from unittest.mock import MagicMock

from src.models import LLMUsage
from src.research.competitor_analyzer import CompetitorAnalyzer


def _make_mock_analyzer(num_ads=2):
    """Create a CompetitorAnalyzer with mocked LLM and minimal ads."""
    mock_client = MagicMock()

    analysis_response = json.dumps({
        "hook_type": "social_proof",
        "angle": "credibility",
        "cta_style": "low_friction",
        "emotional_triggers": ["trust", "confidence"],
        "structural_template": "Statistic lead → benefit → CTA",
        "key_differentiator": "Uses specific numbers for credibility",
        "estimated_effectiveness": "high",
    })
    mock_usage = LLMUsage(
        model="gemini-2.5-pro", input_tokens=400, output_tokens=150,
        cost_usd=0.003, call_type="research",
    )
    mock_client.generate.return_value = (analysis_response, mock_usage)

    # Write temp ads file
    import tempfile
    ads = [
        {
            "id": f"comp-test-{i}",
            "source": "TestBrand",
            "primary_text": f"Test ad {i}",
            "headline": "Test Headline",
            "description": "Test desc",
            "cta": "Learn More",
        }
        for i in range(num_ads)
    ]
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(ads, tmp)
    tmp.close()

    analyzer = CompetitorAnalyzer(mock_client, ads_path=tmp.name)
    return analyzer, mock_client, tmp.name


class TestCompetitorAnalyzer:
    def test_analyze_ad_returns_all_fields(self):
        """analyze_ad() should return a dict with all expected pattern fields."""
        analyzer, _, tmp_path = _make_mock_analyzer(1)
        ad = {"id": "test", "source": "Test", "primary_text": "Ad", "headline": "H",
              "description": "D", "cta": "Learn More"}
        analysis, usage = analyzer.analyze_ad(ad)
        assert "hook_type" in analysis
        assert "angle" in analysis
        assert "emotional_triggers" in analysis
        assert "estimated_effectiveness" in analysis
        assert analysis["source"] == "Test"
        import os
        os.unlink(tmp_path)

    def test_analyze_batch_returns_all_ads(self):
        """analyze_batch() should return one analysis per ad."""
        analyzer, _, tmp_path = _make_mock_analyzer(3)
        analyses, usage = analyzer.analyze_batch()
        assert len(analyses) == 3
        assert usage.call_type == "research"
        assert usage.cost_usd > 0
        import os
        os.unlink(tmp_path)

    def test_extract_top_patterns_frequency_counts(self):
        """extract_top_patterns() should count hook types correctly."""
        analyses = [
            {"hook_type": "question", "estimated_effectiveness": "high"},
            {"hook_type": "question", "estimated_effectiveness": "medium"},
            {"hook_type": "statistic", "estimated_effectiveness": "high"},
            {"hook_type": "empathy", "estimated_effectiveness": "low"},
        ]
        patterns = CompetitorAnalyzer.extract_top_patterns(analyses)
        # question appears 2x, should be first
        assert patterns[0]["type"] == "question"
        assert patterns[0]["count"] == 2
        assert patterns[0]["effectiveness_rate"] == 0.5  # 1 high out of 2

    def test_extract_top_patterns_empty_list(self):
        """extract_top_patterns() should handle empty input gracefully."""
        patterns = CompetitorAnalyzer.extract_top_patterns([])
        assert patterns == []
