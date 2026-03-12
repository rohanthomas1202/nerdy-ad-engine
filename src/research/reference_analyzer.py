"""Reference ad analyzer — finds patterns in high vs low performing ads."""

import json
from pathlib import Path

from src.llm.client import GeminiClient
from src.llm.prompts import REFERENCE_ANALYSIS_PROMPT
from src.models import LLMUsage

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class ReferenceAnalyzer:
    """Analyzes reference ads to find performance-correlated patterns."""

    def __init__(self, client: GeminiClient, refs_path: str | None = None):
        self._client = client
        if refs_path is None:
            refs_path = str(PROJECT_ROOT / "data" / "reference_ads.json")
        with open(refs_path) as f:
            self._refs = json.load(f)

    def analyze_performance_correlations(self) -> tuple[dict, LLMUsage]:
        """Compare high-tier vs low-tier ads to extract performance patterns."""
        high_ads = [a for a in self._refs if a.get("performance_tier") == "high"]
        low_ads = [a for a in self._refs if a.get("performance_tier") == "low"]

        def _format_ads(ads: list[dict]) -> str:
            parts = []
            for a in ads:
                parts.append(
                    f"[{a['id']}]\n"
                    f"Primary: {a['primary_text']}\n"
                    f"Headline: {a['headline']}\n"
                    f"CTA: {a['cta']}"
                )
            return "\n\n".join(parts)

        prompt = REFERENCE_ANALYSIS_PROMPT.format(
            high_tier_ads=_format_ads(high_ads),
            low_tier_ads=_format_ads(low_ads),
        )

        text, usage = self._client.generate(
            prompt, model_type="pro", call_type="research",
        )

        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        correlations = json.loads(text)
        return correlations, usage
