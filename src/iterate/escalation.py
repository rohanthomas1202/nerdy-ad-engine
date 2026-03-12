"""Escalation manager — decides when to continue editing, escalate, or abandon."""

from src.llm.prompts import ESCALATION_GENERATION_PROMPT
from src.models import Brief, Diagnosis


class EscalationManager:
    """Routes ads through continue/escalate/abandon decision tree."""

    def __init__(self, max_attempts: int = 3):
        self._max_attempts = max_attempts

    def should_continue(
        self,
        attempt: int,
        current_score: float,
        previous_score: float | None = None,
    ) -> str:
        """Decide whether to continue editing, escalate, or abandon.

        Returns:
            "continue" — keep editing (score improving or early attempt)
            "escalate" — score regressed, try fresh generation with new angle
            "abandon" — max attempts reached, give up
        """
        if attempt >= self._max_attempts:
            return "abandon"

        if previous_score is not None and current_score < previous_score - 0.1:
            return "escalate"

        return "continue"

    def escalate(self, brief: Brief, diagnosis: Diagnosis) -> str:
        """Generate a new variant instruction informed by what failed.

        Returns a modified variant approach instruction for fresh generation.
        """
        return ESCALATION_GENERATION_PROMPT.format(
            audience_segment=brief.audience_segment,
            product=brief.product,
            campaign_goal=brief.campaign_goal,
            failed_dimension=diagnosis.weakest_dimension,
            problem_description=diagnosis.problem_description,
        )
