"""Tests for BriefInterpreter — config-driven brief enrichment."""

from src.generate.brief_interpreter import BriefInterpreter
from src.models import Brief


class TestBriefInterpreter:
    def test_interpret_adds_enrichment_context(self, sample_brief):
        """interpret() should populate enrichment_context."""
        interpreter = BriefInterpreter()
        enriched = interpreter.interpret(sample_brief)
        assert enriched.enrichment_context is not None
        assert len(enriched.enrichment_context) > 0

    def test_enrichment_includes_brand_voice(self, sample_brief):
        """Enrichment should include brand voice attributes."""
        interpreter = BriefInterpreter()
        enriched = interpreter.interpret(sample_brief)
        ctx = enriched.enrichment_context
        assert "empowering" in ctx.lower() or "VOICE" in ctx

    def test_enrichment_includes_audience_context(self):
        """Parent-audience briefs should include parent-specific triggers."""
        interpreter = BriefInterpreter()
        parent_brief = Brief(
            id="test-parent",
            audience_segment="parents_anxious",
            product="SAT Test Prep",
            campaign_goal="conversion",
        )
        enriched = interpreter.interpret(parent_brief)
        ctx = enriched.enrichment_context
        assert "parent" in ctx.lower() or "Parents" in ctx

    def test_student_audience_different_from_parent(self):
        """Student briefs should have different triggers than parent briefs."""
        interpreter = BriefInterpreter()
        parent_brief = Brief(
            id="test-p", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        student_brief = Brief(
            id="test-s", audience_segment="students_stressed",
            product="SAT", campaign_goal="conversion",
        )
        parent_ctx = interpreter.interpret(parent_brief).enrichment_context
        student_ctx = interpreter.interpret(student_brief).enrichment_context
        assert parent_ctx != student_ctx

    def test_load_briefs_parses_yaml(self):
        """load_briefs() should return a list of Brief objects from config."""
        interpreter = BriefInterpreter()
        briefs = interpreter.load_briefs()
        assert len(briefs) >= 10
        assert all(isinstance(b, Brief) for b in briefs)
        assert all(b.id for b in briefs)

    def test_enrichment_includes_key_message(self):
        """If brief has a key_message, it should appear in enrichment."""
        interpreter = BriefInterpreter()
        brief = Brief(
            id="test-msg",
            audience_segment="parents_anxious",
            product="SAT",
            campaign_goal="conversion",
            key_message="200+ point improvement guaranteed",
        )
        enriched = interpreter.interpret(brief)
        assert "200+ point" in enriched.enrichment_context
