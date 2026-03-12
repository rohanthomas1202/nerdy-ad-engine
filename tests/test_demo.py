"""Tests for demo mode — runs without crash, expected output sections."""

import json
from unittest.mock import MagicMock

from src.demo import run_demo
from src.main import Pipeline
from src.models import AdCopy, LLMUsage


def _make_demo_pipeline():
    """Create a Pipeline with mocked LLM for demo testing."""
    mock_client = MagicMock()

    mock_ad = AdCopy(
        primary_text="Expert SAT tutoring that fits your schedule and your goals.",
        headline="SAT Prep That Works",
        description="1-on-1 tutoring. Free first session.",
        cta="Try Free",
    )
    gen_usage = LLMUsage(
        model="gemini-2.0-flash", input_tokens=300, output_tokens=100,
        cost_usd=0.0001, call_type="generation",
    )
    mock_client.generate_structured.return_value = (mock_ad, gen_usage)

    scores_data = [
        {"dimension": "clarity", "score": 8.0, "rationale": "Clear", "confidence": 0.9},
        {"dimension": "value_proposition", "score": 7.5, "rationale": "Good", "confidence": 0.85},
        {"dimension": "call_to_action", "score": 7.0, "rationale": "OK", "confidence": 0.8},
        {"dimension": "brand_voice", "score": 8.5, "rationale": "On-brand", "confidence": 0.9},
        {"dimension": "emotional_resonance", "score": 7.0,
         "rationale": "Decent", "confidence": 0.8},
    ]
    mock_scores_json = json.dumps({"scores": scores_data})
    eval_usage = LLMUsage(
        model="gemini-2.0-pro", input_tokens=500, output_tokens=200,
        cost_usd=0.002, call_type="evaluation",
    )
    mock_client.generate.return_value = (mock_scores_json, eval_usage)
    mock_client.total_cost = 0.005

    return Pipeline(client=mock_client)


class TestDemo:
    def test_demo_runs_without_crash(self):
        """Demo mode should complete without raising exceptions."""
        pipeline = _make_demo_pipeline()
        # Should not raise
        run_demo(pipeline, port=8020)

    def test_demo_output_contains_expected_sections(self, capsys):
        """Demo output should include all 5 sections."""
        pipeline = _make_demo_pipeline()
        run_demo(pipeline, port=8025)

        captured = capsys.readouterr().out
        assert "DEMO MODE" in captured
        assert "EVALUATOR CALIBRATION" in captured
        assert "SINGLE BRIEF PIPELINE" in captured
        assert "QUALITY SUMMARY" in captured
        assert "COST BREAKDOWN" in captured
        assert "TOP ADS" in captured
        assert "DEMO COMPLETE" in captured
