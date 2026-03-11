"""5-dimension ad scorer — the most important module in the system."""

import json
from pathlib import Path

import yaml

from src.llm.client import GeminiClient
from src.llm.prompts import EVALUATION_SCORE_PROMPT, EVALUATION_SYSTEM_PROMPT
from src.models import AdCopy, DimensionScore, LLMUsage

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class DimensionScorer:
    """Scores ad copy across 5 independent quality dimensions using Gemini Pro."""

    def __init__(self, client: GeminiClient, dimensions_path: str | None = None):
        self._client = client

        if dimensions_path is None:
            dimensions_path = str(PROJECT_ROOT / "config" / "dimensions.yaml")
        with open(dimensions_path) as f:
            self._dimensions_config = yaml.safe_load(f)["dimensions"]

    def _build_rubric_text(self) -> str:
        """Build the dimensions rubric text for the evaluation prompt."""
        lines = []
        for dim in self._dimensions_config:
            lines.append(f"## {dim['name'].upper()} (weight: {dim['weight']})")
            lines.append(f"Description: {dim['description']}")
            lines.append(f"Measures: {', '.join(dim['measures'])}")
            lines.append(f"Low (1-3): {dim['rubric']['low']}")
            lines.append(f"Mid (4-6): {dim['rubric']['mid']}")
            lines.append(f"High (7-10): {dim['rubric']['high']}")
            lines.append("")
        return "\n".join(lines)

    def _build_calibration_examples(self) -> str:
        """Build calibration example text from dimension config."""
        lines = []
        for dim in self._dimensions_config:
            cal = dim.get("calibration_examples", {})
            if cal:
                low = cal.get("low_example", {})
                high = cal.get("high_example", {})
                if low:
                    lines.append(
                        f"[{dim['name']}] Low example (expected ~{low['expected_score']}): "
                        f'"{low["text"]}"'
                    )
                if high:
                    lines.append(
                        f"[{dim['name']}] High example (expected ~{high['expected_score']}): "
                        f'"{high["text"]}"'
                    )
        return "\n".join(lines)

    def score(self, ad_copy: AdCopy) -> tuple[list[DimensionScore], LLMUsage]:
        """Score an ad across all 5 dimensions. Returns (scores, usage)."""
        prompt = (
            EVALUATION_SYSTEM_PROMPT
            + "\n\n"
            + EVALUATION_SCORE_PROMPT.format(
                primary_text=ad_copy.primary_text,
                headline=ad_copy.headline,
                description=ad_copy.description,
                cta=ad_copy.cta,
                dimensions_rubric=self._build_rubric_text(),
                calibration_examples=self._build_calibration_examples(),
            )
        )

        text, usage = self._client.generate(
            prompt=prompt,
            model_type="pro",
            call_type="evaluation",
        )

        scores = self._parse_scores(text)
        return scores, usage

    def _parse_scores(self, text: str) -> list[DimensionScore]:
        """Parse LLM JSON response into DimensionScore objects."""
        data = json.loads(text)

        # Handle both {"scores": [...]} and direct list
        raw_scores = data if isinstance(data, list) else data.get("scores", data)

        expected_dims = {d["name"] for d in self._dimensions_config}
        scores = []
        for item in raw_scores:
            score = DimensionScore(
                dimension=item["dimension"],
                score=float(item["score"]),
                rationale=item["rationale"],
                confidence=float(item.get("confidence", 0.8)),
            )
            scores.append(score)

        # Validate we got all 5 dimensions
        got_dims = {s.dimension for s in scores}
        missing = expected_dims - got_dims
        if missing:
            raise ValueError(f"Missing dimension scores: {missing}")

        return scores
