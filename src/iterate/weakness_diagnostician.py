"""Weakness diagnostician — dimension-level diagnosis for targeted editing."""

import json

from src.llm.client import GeminiClient
from src.llm.prompts import DIAGNOSIS_PROMPT
from src.models import AdCopy, Diagnosis, EvaluationResult, LLMUsage


class WeaknessDiagnostician:
    """Diagnoses the weakest dimension and produces specific, actionable fixes."""

    def __init__(self, client: GeminiClient):
        self._client = client

    def diagnose(
        self, ad_copy: AdCopy, evaluation: EvaluationResult
    ) -> tuple[Diagnosis, LLMUsage]:
        """Diagnose the weakest dimension and suggest a targeted fix.

        Returns:
            (Diagnosis, LLMUsage) with specific problem description and fix.
        """
        weakest = evaluation.weakest_dimension
        weakest_score = next(
            s for s in evaluation.dimension_scores if s.dimension == weakest
        )

        # Dimensions scoring well that must be preserved
        preserve = [
            s.dimension
            for s in evaluation.dimension_scores
            if s.score >= 7.0 and s.dimension != weakest
        ]

        scores_text = "\n".join(
            f"  - {s.dimension}: {s.score:.1f} — {s.rationale}"
            for s in evaluation.dimension_scores
        )

        prompt = DIAGNOSIS_PROMPT.format(
            primary_text=ad_copy.primary_text,
            headline=ad_copy.headline,
            description=ad_copy.description,
            cta=ad_copy.cta,
            dimension_scores=scores_text,
            weakest_dimension=weakest,
            weakest_score=weakest_score.score,
            weakest_rationale=weakest_score.rationale,
        )

        text, usage = self._client.generate(
            prompt=prompt,
            model_type="pro",
            call_type="editing",
        )

        data = json.loads(text)
        diagnosis = Diagnosis(
            weakest_dimension=weakest,
            score=weakest_score.score,
            problem_description=data["problem_description"],
            suggested_fix=data["suggested_fix"],
            preserve_dimensions=preserve,
        )

        return diagnosis, usage
