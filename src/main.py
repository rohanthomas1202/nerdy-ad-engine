"""Orchestrator — entry point for the ad generation pipeline."""

import json
import uuid
from pathlib import Path

from src.evaluate.aggregator import Aggregator
from src.evaluate.dimension_scorer import DimensionScorer
from src.evaluate.quality_gate import QualityGate
from src.generate.brief_interpreter import BriefInterpreter
from src.generate.variant_strategy import VariantStrategy
from src.generate.writer import Writer
from src.llm.client import GeminiClient
from src.models import AdRecord, Brief

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Pipeline:
    """Orchestrates the full generate → evaluate → route pipeline."""

    def __init__(self, client: GeminiClient | None = None):
        self._client = client or GeminiClient()
        self._interpreter = BriefInterpreter()
        self._writer = Writer(self._client)
        self._strategy = VariantStrategy()
        self._scorer = DimensionScorer(self._client)
        self._aggregator = Aggregator()
        self._gate = QualityGate()

    def run_single_brief(self, brief: Brief) -> list[AdRecord]:
        """Process a single brief: enrich → generate 3 variants → evaluate each."""
        enriched = self._interpreter.interpret(brief)
        approaches = self._strategy.select_approaches(enriched)

        records = []
        for i, approach in enumerate(approaches):
            record = self._generate_and_evaluate(enriched, approach, i)
            records.append(record)
            print(
                f"  Variant {i + 1}/{len(approaches)}: "
                f"score={record.evaluation.aggregate_score:.2f} "
                f"[{record.status}]"
            )

        return records

    def _generate_and_evaluate(
        self, brief: Brief, approach: str, variant_index: int
    ) -> AdRecord:
        """Generate one ad variant and evaluate it."""
        ad_id = f"{brief.id}-v{variant_index}-{uuid.uuid4().hex[:6]}"

        # Generate
        ad_copy, gen_usage = self._writer.write(brief, approach)

        # Evaluate
        scores, eval_usage = self._scorer.score(ad_copy)
        evaluation = self._aggregator.aggregate(scores)

        # Route through quality gate (no editing in Phase 2 — mark as failed)
        gate_result = self._gate.check(evaluation)
        status = "approved" if gate_result == "approved" else "failed"

        gen_cost = gen_usage.cost_usd
        eval_cost = eval_usage.cost_usd

        return AdRecord(
            id=ad_id,
            brief_id=brief.id,
            variant_index=variant_index,
            ad_copy=ad_copy,
            evaluation=evaluation,
            status=status,
            generation_cost_usd=gen_cost,
            evaluation_cost_usd=eval_cost,
            total_cost_usd=gen_cost + eval_cost,
            model_used=gen_usage.model,
        )

    def run_batch(self, briefs: list[Brief] | None = None) -> list[AdRecord]:
        """Run the pipeline for a batch of briefs."""
        if briefs is None:
            briefs = self._interpreter.load_briefs()

        all_records = []
        for i, brief in enumerate(briefs):
            print(f"\nBrief {i + 1}/{len(briefs)}: {brief.id}")
            records = self.run_single_brief(brief)
            all_records.extend(records)

        self.save_results(all_records)
        self._print_summary(all_records)
        return all_records

    def save_results(self, records: list[AdRecord]) -> None:
        """Save approved and failed ads to output JSON files."""
        output_dir = PROJECT_ROOT / "output"
        output_dir.mkdir(exist_ok=True)

        approved = [r.model_dump(mode="json") for r in records if r.status == "approved"]
        failed = [r.model_dump(mode="json") for r in records if r.status != "approved"]

        with open(output_dir / "ad_library.json", "w") as f:
            json.dump(approved, f, indent=2, default=str)

        with open(output_dir / "failed_ads.json", "w") as f:
            json.dump(failed, f, indent=2, default=str)

    def _print_summary(self, records: list[AdRecord]) -> None:
        """Print a summary of the pipeline run."""
        total = len(records)
        approved = sum(1 for r in records if r.status == "approved")
        failed = total - approved
        avg_score = (
            sum(r.evaluation.aggregate_score for r in records if r.evaluation) / total
            if total
            else 0
        )
        total_cost = self._client.total_cost

        print(f"\n{'=' * 50}")
        print("PIPELINE SUMMARY")
        print(f"{'=' * 50}")
        print(f"Total ads:     {total}")
        print(f"Approved:      {approved} ({approved / total * 100:.0f}%)" if total else "")
        print(f"Failed:        {failed}")
        print(f"Avg score:     {avg_score:.2f}")
        print(f"Total cost:    ${total_cost:.4f}")
        print(f"{'=' * 50}")


def main():
    pipeline = Pipeline()
    pipeline.run_batch()


if __name__ == "__main__":
    main()
