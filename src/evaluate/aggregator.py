"""Weighted score aggregation and evaluation result construction."""

from pathlib import Path

import yaml

from src.models import DimensionScore, EvaluationResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Aggregator:
    """Combines 5 dimension scores into a weighted aggregate with quality gate check."""

    def __init__(self, settings_path: str | None = None):
        if settings_path is None:
            settings_path = str(PROJECT_ROOT / "config" / "settings.yaml")
        with open(settings_path) as f:
            settings = yaml.safe_load(f)

        self._weights = settings["weights"]
        self._threshold = settings["thresholds"]["quality_gate"]

    def aggregate(self, dimension_scores: list[DimensionScore]) -> EvaluationResult:
        """Compute weighted average, identify weakest dimension, check quality gate."""
        # Compute weighted average
        total_weight = 0.0
        weighted_sum = 0.0
        for ds in dimension_scores:
            weight = self._weights.get(ds.dimension, 0.0)
            weighted_sum += ds.score * weight
            total_weight += weight

        aggregate_score = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

        # Find weakest dimension
        weakest = min(dimension_scores, key=lambda ds: ds.score)

        # Quality gate
        passed = aggregate_score >= self._threshold

        # Build rationale
        score_summary = ", ".join(
            f"{ds.dimension}: {ds.score:.1f}" for ds in dimension_scores
        )
        rationale = (
            f"Aggregate: {aggregate_score:.2f} ({'PASS' if passed else 'FAIL'}). "
            f"Scores: [{score_summary}]. "
            f"Weakest: {weakest.dimension} ({weakest.score:.1f})."
        )

        return EvaluationResult(
            dimension_scores=dimension_scores,
            aggregate_score=aggregate_score,
            passed_quality_gate=passed,
            weakest_dimension=weakest.dimension,
            evaluation_rationale=rationale,
        )
