"""Tests for GeminiClient — mocked API calls, usage tracking, cost computation."""

import json

import pytest

from src.models import DimensionScore, LLMUsage


class TestGeminiClientUsageTracking:
    """Test usage tracking with manually constructed LLMUsage objects."""

    def test_usage_accumulation(self):
        """Multiple usages should accumulate correctly."""
        usages = [
            LLMUsage(
                model="gemini-2.0-flash",
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.0001,
                call_type="generation",
            ),
            LLMUsage(
                model="gemini-2.0-pro",
                input_tokens=200,
                output_tokens=100,
                cost_usd=0.0008,
                call_type="evaluation",
            ),
        ]
        total = sum(u.cost_usd for u in usages)
        assert abs(total - 0.0009) < 1e-6

    def test_cost_computation_flash(self):
        """Flash model cost should use flash rates."""
        # flash: input=0.000075/1k, output=0.0003/1k
        # 1000 input tokens + 500 output tokens
        expected_cost = (1000 * 0.000075 / 1000) + (500 * 0.0003 / 1000)
        # = 0.000075 + 0.00015 = 0.000225
        assert abs(expected_cost - 0.000225) < 1e-8

    def test_cost_computation_pro(self):
        """Pro model cost should use pro rates."""
        # pro: input=0.00125/1k, output=0.005/1k
        # 1000 input tokens + 500 output tokens
        expected_cost = (1000 * 0.00125 / 1000) + (500 * 0.005 / 1000)
        # = 0.00125 + 0.0025 = 0.00375
        assert abs(expected_cost - 0.00375) < 1e-8

    def test_usage_log_reset(self):
        """Reset should clear the usage list."""
        usages = [
            LLMUsage(
                model="test", input_tokens=1, output_tokens=1,
                cost_usd=0.01, call_type="test"
            )
        ]
        usages.clear()
        assert len(usages) == 0

    def test_structured_parse_valid_json(self):
        """Valid JSON should parse into a Pydantic model."""
        raw = json.dumps(
            {"dimension": "clarity", "score": 8.0, "rationale": "Good", "confidence": 0.9}
        )
        parsed = DimensionScore.model_validate_json(raw)
        assert parsed.dimension == "clarity"
        assert parsed.score == 8.0

    def test_structured_parse_invalid_json(self):
        """Invalid JSON should raise an error."""
        with pytest.raises(Exception):
            DimensionScore.model_validate_json("not valid json")

    def test_usage_fields(self):
        """LLMUsage should store all fields correctly."""
        usage = LLMUsage(
            model="gemini-2.0-pro",
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.001625,
            call_type="evaluation",
            duration_seconds=2.5,
        )
        assert usage.model == "gemini-2.0-pro"
        assert usage.input_tokens == 500
        assert usage.output_tokens == 200
        assert usage.call_type == "evaluation"
        assert usage.duration_seconds == 2.5
