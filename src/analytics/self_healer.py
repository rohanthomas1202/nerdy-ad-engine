"""Self-healer — detects quality regressions and diagnoses root causes."""

import json

from src.llm.client import GeminiClient
from src.llm.prompts import SELF_HEAL_DIAGNOSIS_PROMPT
from src.models import AdRecord, LLMUsage


class SelfHealer:
    """Diagnoses quality regressions and suggests prompt/strategy fixes."""

    def __init__(self, client: GeminiClient):
        self._client = client

    def diagnose_regression(
        self,
        regression: dict,
        recent_records: list[AdRecord],
    ) -> tuple[str, LLMUsage]:
        """Diagnose why a dimension regressed.

        Args:
            regression: Dict with dimension, previous_avg, current_avg, drop.
            recent_records: Records from the regressed cycle.

        Returns:
            (diagnosis_text, usage)
        """
        dim = regression["dimension"]

        # Find ads scoring poorly on this dimension
        poor_ads = []
        for r in recent_records:
            if r.evaluation:
                for ds in r.evaluation.dimension_scores:
                    if ds.dimension == dim and ds.score < 6.5:
                        poor_ads.append(r)
                        break

        # Format sample ads for the prompt
        samples = []
        for r in poor_ads[:5]:
            samples.append(
                f"Primary: {r.ad_copy.primary_text}\n"
                f"Headline: {r.ad_copy.headline}\n"
                f"Score on {dim}: "
                f"{next((ds.score for ds in r.evaluation.dimension_scores if ds.dimension == dim), '?')}"
            )
        sample_text = "\n\n".join(samples) if samples else "No samples available."

        prompt = SELF_HEAL_DIAGNOSIS_PROMPT.format(
            dimension=dim,
            previous_avg=regression["previous_avg"],
            current_avg=regression["current_avg"],
            drop=regression["drop"],
            sample_ads=sample_text,
        )

        text, usage = self._client.generate(
            prompt, model_type="pro", call_type="self_healing",
        )
        return text, usage

    def suggest_fix(self, diagnosis_text: str) -> str:
        """Extract the suggested fix from a diagnosis response."""
        try:
            # Strip markdown fences
            text = diagnosis_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())
            return data.get("suggested_fix", diagnosis_text)
        except (json.JSONDecodeError, AttributeError):
            return diagnosis_text

    def heal(
        self,
        regressions: list[dict],
        recent_records: list[AdRecord],
    ) -> list[dict]:
        """Diagnose and suggest fixes for all regressions.

        Returns list of {dimension, diagnosis, fix}.
        """
        results = []
        for reg in regressions:
            diagnosis_text, _ = self.diagnose_regression(reg, recent_records)
            fix = self.suggest_fix(diagnosis_text)

            try:
                text = diagnosis_text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                data = json.loads(text.strip())
                diagnosis = data.get("diagnosis", diagnosis_text)
            except (json.JSONDecodeError, AttributeError):
                diagnosis = diagnosis_text

            results.append({
                "dimension": reg["dimension"],
                "diagnosis": diagnosis,
                "fix": fix,
            })

        return results
