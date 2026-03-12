"""Targeted editor — surgical rewrites preserving strong dimensions."""

from src.llm.client import GeminiClient
from src.llm.prompts import EDITING_PROMPT
from src.models import AdCopy, Diagnosis, LLMUsage


class TargetedEditor:
    """Edits ad copy to improve a specific weak dimension without regressing others."""

    def __init__(self, client: GeminiClient):
        self._client = client

    def edit(
        self, ad_copy: AdCopy, diagnosis: Diagnosis
    ) -> tuple[AdCopy, LLMUsage]:
        """Surgically edit ad copy based on diagnosis.

        Args:
            ad_copy: The current ad copy to improve.
            diagnosis: Specific diagnosis with fix instructions.

        Returns:
            (AdCopy, LLMUsage) with targeted improvements.
        """
        preserve_text = (
            ", ".join(diagnosis.preserve_dimensions)
            if diagnosis.preserve_dimensions
            else "none identified"
        )

        prompt = EDITING_PROMPT.format(
            primary_text=ad_copy.primary_text,
            headline=ad_copy.headline,
            description=ad_copy.description,
            cta=ad_copy.cta,
            weakest_dimension=diagnosis.weakest_dimension,
            problem_description=diagnosis.problem_description,
            suggested_fix=diagnosis.suggested_fix,
            preserve_dimensions=preserve_text,
        )

        edited_copy, usage = self._client.generate_structured(
            prompt=prompt,
            response_type=AdCopy,
            model_type="pro",
            temperature=0.3,
            call_type="editing",
        )

        return edited_copy, usage
