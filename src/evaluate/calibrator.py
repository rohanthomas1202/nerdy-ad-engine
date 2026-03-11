"""Evaluator calibration against reference ads — validates the evaluator works."""

import json
from pathlib import Path

from src.evaluate.aggregator import Aggregator
from src.evaluate.dimension_scorer import DimensionScorer
from src.models import AdCopy, CalibrationResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Tier ordinals for correlation
TIER_ORDINAL = {"high": 3, "medium": 2, "low": 1}


class Calibrator:
    """Validates that the evaluator can distinguish quality tiers in reference ads."""

    def __init__(
        self,
        scorer: DimensionScorer,
        aggregator: Aggregator,
        reference_path: str | None = None,
    ):
        self._scorer = scorer
        self._aggregator = aggregator

        if reference_path is None:
            reference_path = str(PROJECT_ROOT / "data" / "reference_ads.json")
        with open(reference_path) as f:
            self._reference_ads = json.load(f)

    def run_calibration(self) -> list[CalibrationResult]:
        """Score all reference ads and check alignment with expected tiers."""
        results = []
        for ref_ad in self._reference_ads:
            ad_copy = AdCopy(
                primary_text=ref_ad["primary_text"],
                headline=ref_ad["headline"],
                description=ref_ad["description"],
                cta=ref_ad["cta"],
            )

            scores, _usage = self._scorer.score(ad_copy)
            evaluation = self._aggregator.aggregate(scores)

            # Check alignment
            tier = ref_ad["performance_tier"]
            aligned = self._check_alignment(tier, evaluation.aggregate_score)

            result = CalibrationResult(
                reference_ad_id=ref_ad["id"],
                expected_tier=tier,
                actual_scores=scores,
                aggregate_score=evaluation.aggregate_score,
                alignment="aligned" if aligned else "misaligned",
            )
            results.append(result)

        return results

    def _check_alignment(self, tier: str, score: float) -> bool:
        """Check if a score aligns with the expected performance tier."""
        if tier == "high":
            return score >= 7.0
        elif tier == "low":
            return score < 5.5
        else:  # medium
            return 4.5 <= score < 8.0

    def report(self, results: list[CalibrationResult]) -> dict:
        """Generate a calibration summary report."""
        total = len(results)
        aligned_count = sum(1 for r in results if r.alignment == "aligned")
        alignment_rate = aligned_count / total if total > 0 else 0.0

        # Average score per tier
        tier_scores: dict[str, list[float]] = {"high": [], "medium": [], "low": []}
        for r in results:
            tier_scores[r.expected_tier].append(r.aggregate_score)

        avg_by_tier = {
            tier: round(sum(scores) / len(scores), 2) if scores else 0.0
            for tier, scores in tier_scores.items()
        }

        # Spearman-like rank check: high avg > medium avg > low avg
        rank_order_correct = avg_by_tier["high"] > avg_by_tier["medium"] > avg_by_tier["low"]

        return {
            "total_ads": total,
            "aligned": aligned_count,
            "misaligned": total - aligned_count,
            "alignment_rate": round(alignment_rate, 3),
            "avg_score_by_tier": avg_by_tier,
            "rank_order_correct": rank_order_correct,
            "results": [r.model_dump() for r in results],
        }


if __name__ == "__main__":
    """Run calibration as a standalone script."""
    from src.llm.client import GeminiClient

    print("=" * 60)
    print("EVALUATOR CALIBRATION")
    print("=" * 60)

    client = GeminiClient()
    scorer = DimensionScorer(client)
    aggregator = Aggregator()
    calibrator = Calibrator(scorer, aggregator)

    print("\nScoring reference ads...")
    results = calibrator.run_calibration()

    for r in results:
        status = "✓" if r.alignment == "aligned" else "✗"
        print(
            f"  {status} {r.reference_ad_id} "
            f"[{r.expected_tier}] → {r.aggregate_score:.2f} "
            f"({r.alignment})"
        )

    report = calibrator.report(results)
    print(f"\n{'=' * 60}")
    print(f"Alignment Rate: {report['alignment_rate']:.1%}")
    print(f"Avg by tier: {report['avg_score_by_tier']}")
    print(f"Rank order correct: {report['rank_order_correct']}")
    print(f"Total LLM cost: ${client.total_cost:.4f}")
    print(f"{'=' * 60}")
