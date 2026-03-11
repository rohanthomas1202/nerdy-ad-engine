"""Tests for Pydantic data models — validation, constraints, and defaults."""

import pytest
from pydantic import ValidationError

from src.models import (
    ALLOWED_CTAS,
    AdCopy,
    AdRecord,
    Brief,
    DimensionScore,
    LLMUsage,
)


class TestAdCopy:
    def test_valid_ad_copy(self, sample_ad_copy):
        assert sample_ad_copy.cta == "Try Free"
        assert len(sample_ad_copy.primary_text) <= 500
        assert len(sample_ad_copy.headline) <= 40

    def test_primary_text_too_long(self):
        with pytest.raises(ValidationError, match="String should have at most 500 characters"):
            AdCopy(
                primary_text="x" * 501,
                headline="Test",
                description="Test",
                cta="Learn More",
            )

    def test_headline_too_long(self):
        with pytest.raises(ValidationError, match="String should have at most 40 characters"):
            AdCopy(
                primary_text="Test",
                headline="x" * 41,
                description="Test",
                cta="Learn More",
            )

    def test_description_too_long(self):
        with pytest.raises(ValidationError, match="String should have at most 125 characters"):
            AdCopy(
                primary_text="Test",
                headline="Test",
                description="x" * 126,
                cta="Learn More",
            )

    def test_invalid_cta(self):
        with pytest.raises(ValidationError, match="CTA must be one of"):
            AdCopy(
                primary_text="Test",
                headline="Test",
                description="Test",
                cta="Buy Now",
            )

    def test_all_valid_ctas(self):
        for cta in ALLOWED_CTAS:
            ad = AdCopy(
                primary_text="Test", headline="Test", description="Test", cta=cta
            )
            assert ad.cta == cta


class TestDimensionScore:
    def test_valid_score(self):
        ds = DimensionScore(
            dimension="clarity", score=7.5, rationale="Good clarity", confidence=0.8
        )
        assert ds.score == 7.5

    def test_score_below_minimum(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            DimensionScore(dimension="clarity", score=0.5, rationale="Bad", confidence=0.8)

    def test_score_above_maximum(self):
        with pytest.raises(ValidationError, match="less than or equal to 10"):
            DimensionScore(dimension="clarity", score=10.5, rationale="Too high", confidence=0.8)

    def test_confidence_below_zero(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            DimensionScore(dimension="clarity", score=5.0, rationale="OK", confidence=-0.1)

    def test_confidence_above_one(self):
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            DimensionScore(dimension="clarity", score=5.0, rationale="OK", confidence=1.1)

    def test_empty_rationale_rejected(self):
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            DimensionScore(dimension="clarity", score=5.0, rationale="", confidence=0.8)


class TestBrief:
    def test_valid_brief(self, sample_brief):
        assert sample_brief.campaign_goal == "conversion"
        assert sample_brief.tone_override is None

    def test_invalid_campaign_goal(self):
        with pytest.raises(ValidationError):
            Brief(
                id="test",
                audience_segment="parents",
                product="SAT",
                campaign_goal="invalid",
            )

    def test_optional_fields_default_none(self):
        b = Brief(
            id="test",
            audience_segment="parents",
            product="SAT",
            campaign_goal="awareness",
        )
        assert b.tone_override is None
        assert b.key_message is None
        assert b.enrichment_context is None


class TestAdRecord:
    def test_default_status_is_draft(self, sample_ad_copy):
        record = AdRecord(
            id="test-001",
            brief_id="brief-001",
            variant_index=0,
            ad_copy=sample_ad_copy,
        )
        assert record.status == "draft"
        assert record.evaluation is None
        assert record.iteration_history == []
        assert record.total_cost_usd == 0.0


class TestLLMUsage:
    def test_valid_usage(self):
        usage = LLMUsage(
            model="gemini-2.0-pro",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            call_type="evaluation",
        )
        assert usage.duration_seconds == 0.0  # default
