"""Tests for EscalationManager — continue/escalate/abandon decision logic."""

from src.iterate.escalation import EscalationManager
from src.models import Brief, Diagnosis


class TestEscalationManager:
    def test_continue_on_first_attempt(self):
        """First attempt should always continue."""
        mgr = EscalationManager(max_attempts=3)
        result = mgr.should_continue(attempt=1, current_score=6.0)
        assert result == "continue"

    def test_continue_on_improvement(self):
        """Should continue if score is improving."""
        mgr = EscalationManager(max_attempts=3)
        result = mgr.should_continue(
            attempt=2, current_score=6.5, previous_score=6.0,
        )
        assert result == "continue"

    def test_abandon_at_max_attempts(self):
        """Should abandon when max attempts reached."""
        mgr = EscalationManager(max_attempts=3)
        result = mgr.should_continue(
            attempt=3, current_score=6.0, previous_score=6.5,
        )
        assert result == "abandon"

    def test_escalate_on_regression(self):
        """Should escalate when score drops significantly."""
        mgr = EscalationManager(max_attempts=3)
        result = mgr.should_continue(
            attempt=2, current_score=5.5, previous_score=6.5,
        )
        assert result == "escalate"

    def test_escalation_references_diagnosis(self):
        """Escalation instruction should reference the failed dimension."""
        mgr = EscalationManager()
        brief = Brief(
            id="test", audience_segment="parents_anxious",
            product="SAT", campaign_goal="conversion",
        )
        diagnosis = Diagnosis(
            weakest_dimension="emotional_resonance",
            score=5.0,
            problem_description="Lacks emotional connection with parents.",
            suggested_fix="Add parent empathy.",
            preserve_dimensions=["clarity"],
        )
        instruction = mgr.escalate(brief, diagnosis)
        assert "emotional_resonance" in instruction
        assert "parents_anxious" in instruction
