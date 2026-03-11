"""Ad copy writer — generates structured ad copy using Gemini Flash."""

from src.llm.client import GeminiClient
from src.llm.prompts import GENERATION_PROMPT, GENERATION_SYSTEM_PROMPT
from src.models import AdCopy, Brief, LLMUsage


class Writer:
    """Generates ad copy from enriched briefs using Gemini Flash."""

    def __init__(self, client: GeminiClient):
        self._client = client

    def write(
        self, enriched_brief: Brief, variant_approach: str
    ) -> tuple[AdCopy, LLMUsage]:
        """Generate a single ad copy variant.

        Args:
            enriched_brief: Brief with enrichment_context populated.
            variant_approach: Instruction string from VariantStrategy.

        Returns:
            (AdCopy, LLMUsage) tuple.
        """
        prompt = (
            GENERATION_SYSTEM_PROMPT
            + "\n\n"
            + GENERATION_PROMPT.format(
                enriched_context=enriched_brief.enrichment_context or "",
                variant_instruction=variant_approach,
            )
        )

        ad_copy, usage = self._client.generate_structured(
            prompt=prompt,
            response_type=AdCopy,
            model_type="flash",
            call_type="generation",
        )

        return ad_copy, usage
