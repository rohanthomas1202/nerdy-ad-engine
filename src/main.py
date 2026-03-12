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
from src.iterate.escalation import EscalationManager
from src.iterate.targeted_editor import TargetedEditor
from src.iterate.weakness_diagnostician import WeaknessDiagnostician
from src.llm.client import GeminiClient
from src.models import AdRecord, Brief

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Pipeline:
    """Orchestrates the full generate → evaluate → iterate → route pipeline."""

    def __init__(self, client: GeminiClient | None = None):
        self._client = client or GeminiClient()
        self._interpreter = BriefInterpreter()
        self._writer = Writer(self._client)
        self._strategy = VariantStrategy()
        self._scorer = DimensionScorer(self._client)
        self._aggregator = Aggregator()
        self._gate = QualityGate()
        self._diagnostician = WeaknessDiagnostician(self._client)
        self._editor = TargetedEditor(self._client)
        self._escalation = EscalationManager()

    def run_single_brief(self, brief: Brief) -> list[AdRecord]:
        """Process a single brief: enrich → generate 3 variants → evaluate → iterate."""
        enriched = self._interpreter.interpret(brief)
        approaches = self._strategy.select_approaches(enriched)

        records = []
        for i, approach in enumerate(approaches):
            record = self._generate_and_evaluate(enriched, approach, i)

            # Iterate on failing ads
            if record.status != "approved":
                record = self._iterate_ad(record, enriched)

            records.append(record)
            status_label = record.status.upper()
            edits = len(record.iteration_history) - 1 if record.iteration_history else 0
            edit_info = f" ({edits} edits)" if edits > 0 else ""
            print(
                f"  Variant {i + 1}/{len(approaches)}: "
                f"score={record.evaluation.aggregate_score:.2f} "
                f"[{status_label}]{edit_info}"
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

        # Route through quality gate
        gate_result = self._gate.check(evaluation)
        status = "approved" if gate_result == "approved" else "draft"

        gen_cost = gen_usage.cost_usd
        eval_cost = eval_usage.cost_usd

        return AdRecord(
            id=ad_id,
            brief_id=brief.id,
            variant_index=variant_index,
            ad_copy=ad_copy,
            evaluation=evaluation,
            iteration_history=[evaluation],
            status=status,
            generation_cost_usd=gen_cost,
            evaluation_cost_usd=eval_cost,
            total_cost_usd=gen_cost + eval_cost,
            model_used=gen_usage.model,
        )

    def _iterate_ad(self, record: AdRecord, brief: Brief) -> AdRecord:
        """Diagnose → edit → re-evaluate loop until approved or max attempts."""
        previous_score = record.evaluation.aggregate_score

        for attempt in range(1, self._escalation._max_attempts + 1):
            # Diagnose weakness
            diagnosis, diag_usage = self._diagnostician.diagnose(
                record.ad_copy, record.evaluation
            )
            record.total_cost_usd += diag_usage.cost_usd

            # Check escalation
            decision = self._escalation.should_continue(
                attempt, record.evaluation.aggregate_score, previous_score
            )

            if decision == "abandon":
                record.status = "failed"
                return record

            if decision == "escalate":
                # Fresh generation with new angle
                new_approach = self._escalation.escalate(brief, diagnosis)
                new_copy, gen_usage = self._writer.write(brief, new_approach)
                record.ad_copy = new_copy
                record.total_cost_usd += gen_usage.cost_usd
            else:
                # Surgical edit
                edited_copy, edit_usage = self._editor.edit(
                    record.ad_copy, diagnosis
                )
                record.ad_copy = edited_copy
                record.total_cost_usd += edit_usage.cost_usd

            # Re-evaluate
            previous_score = record.evaluation.aggregate_score
            scores, eval_usage = self._scorer.score(record.ad_copy)
            evaluation = self._aggregator.aggregate(scores)
            record.evaluation = evaluation
            record.iteration_history.append(evaluation)
            record.evaluation_cost_usd += eval_usage.cost_usd
            record.total_cost_usd += eval_usage.cost_usd

            print(
                f"    Edit {attempt}: "
                f"{previous_score:.2f} → {evaluation.aggregate_score:.2f} "
                f"[{diagnosis.weakest_dimension}]"
            )

            # Check gate
            gate_result = self._gate.check(evaluation)
            if gate_result == "approved":
                record.status = "approved"
                return record

        record.status = "failed"
        return record

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

        # Iteration stats
        edited = sum(1 for r in records if len(r.iteration_history) > 1)
        rescued = sum(
            1 for r in records
            if r.status == "approved" and len(r.iteration_history) > 1
        )

        print(f"\n{'=' * 50}")
        print("PIPELINE SUMMARY")
        print(f"{'=' * 50}")
        print(f"Total ads:     {total}")
        if total:
            print(f"Approved:      {approved} ({approved / total * 100:.0f}%)")
        print(f"Failed:        {failed}")
        print(f"Avg score:     {avg_score:.2f}")
        print(f"Edited:        {edited} ads entered iteration loop")
        print(f"Rescued:       {rescued} ads saved by editing")
        print(f"Total cost:    ${total_cost:.4f}")
        print(f"{'=' * 50}")


def main():
    pipeline = Pipeline()
    pipeline.run_batch()


if __name__ == "__main__":
    main()
