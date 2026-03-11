"""Tests for VariantStrategy — diverse approach selection."""

from src.generate.variant_strategy import APPROACHES, VariantStrategy
from src.models import Brief


class TestVariantStrategy:
    def test_returns_exact_count(self):
        """select_approaches() should return exactly `count` approaches."""
        strategy = VariantStrategy()
        brief = Brief(
            id="test", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        approaches = strategy.select_approaches(brief, count=3)
        assert len(approaches) == 3

    def test_approaches_are_unique_strings(self):
        """Each returned approach should be a unique instruction string."""
        strategy = VariantStrategy()
        brief = Brief(
            id="test", audience_segment="students_stressed",
            product="SAT", campaign_goal="awareness",
        )
        approaches = strategy.select_approaches(brief, count=3)
        assert len(set(approaches)) == 3

    def test_parent_audience_gets_relevant_approaches(self):
        """Parent briefs should prioritize parent-relevant angles."""
        strategy = VariantStrategy()
        brief = Brief(
            id="test", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        approaches = strategy.select_approaches(brief, count=3)
        # At least one approach should mention parent/anxiety/empathy
        combined = " ".join(approaches).lower()
        assert any(
            word in combined
            for word in ["parent", "anxiety", "stress", "empathy", "overwhelm"]
        )

    def test_enough_approaches_for_two_briefs(self):
        """APPROACHES list should have at least 6 entries."""
        assert len(APPROACHES) >= 6

    def test_different_audiences_get_different_approaches(self):
        """Parent and student briefs should get different first approaches."""
        strategy = VariantStrategy()
        parent = Brief(
            id="p", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        student = Brief(
            id="s", audience_segment="students_stressed",
            product="SAT", campaign_goal="conversion",
        )
        parent_approaches = strategy.select_approaches(parent, count=3)
        student_approaches = strategy.select_approaches(student, count=3)
        # At least one approach should differ
        assert parent_approaches != student_approaches
