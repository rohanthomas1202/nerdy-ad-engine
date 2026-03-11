"""Tests for Writer — LLM-based ad copy generation."""

from unittest.mock import MagicMock

from src.generate.writer import Writer
from src.models import AdCopy, Brief, LLMUsage


def _mock_writer_client():
    """Create a mock client that returns a valid AdCopy JSON."""
    mock_ad = AdCopy(
        primary_text="Your SAT score can improve 200+ points with expert tutoring.",
        headline="Boost Your SAT Score",
        description="Personalized 1-on-1 tutoring matched to you. Free first session.",
        cta="Try Free",
    )
    mock_usage = LLMUsage(
        model="gemini-2.0-flash",
        input_tokens=300,
        output_tokens=100,
        cost_usd=0.0001,
        call_type="generation",
    )
    client = MagicMock()
    client.generate_structured.return_value = (mock_ad, mock_usage)
    return client


class TestWriter:
    def test_write_returns_valid_ad_copy(self):
        """write() should return a valid AdCopy object."""
        client = _mock_writer_client()
        writer = Writer(client)
        brief = Brief(
            id="test", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
            enrichment_context="Test context",
        )
        ad_copy, usage = writer.write(brief, "Use a question hook.")
        assert isinstance(ad_copy, AdCopy)
        assert len(ad_copy.primary_text) <= 500
        assert len(ad_copy.headline) <= 40

    def test_write_tracks_usage(self):
        """write() should return LLMUsage with cost data."""
        client = _mock_writer_client()
        writer = Writer(client)
        brief = Brief(
            id="test", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
            enrichment_context="Test context",
        )
        _, usage = writer.write(brief, "Use a question hook.")
        assert isinstance(usage, LLMUsage)
        assert usage.call_type == "generation"
        assert usage.cost_usd > 0

    def test_write_uses_flash_model(self):
        """Generation should use Gemini Flash, not Pro."""
        client = _mock_writer_client()
        writer = Writer(client)
        brief = Brief(
            id="test", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
            enrichment_context="Test context",
        )
        writer.write(brief, "Use a question hook.")
        call_kwargs = client.generate_structured.call_args.kwargs
        assert call_kwargs.get("model_type") == "flash"

    def test_prompt_includes_variant_instruction(self):
        """The generation prompt should contain the variant approach."""
        client = _mock_writer_client()
        writer = Writer(client)
        brief = Brief(
            id="test", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
            enrichment_context="Test context",
        )
        instruction = "Open with a provocative statistic about SAT scores."
        writer.write(brief, instruction)
        call_args = client.generate_structured.call_args
        prompt = call_args.kwargs.get("prompt") or call_args.args[0]
        assert "provocative statistic" in prompt
