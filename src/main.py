"""Orchestrator — entry point for the ad generation pipeline."""

import argparse
import json
import random
import sys
import uuid
from pathlib import Path

from src.analytics.experiment_logger import ExperimentLogger
from src.analytics.quality_ratchet import QualityRatchet
from src.analytics.quality_tracker import QualityTracker
from src.analytics.self_healer import SelfHealer
from src.analytics.token_tracker import TokenTracker
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
from src.models import AdRecord, Brief, ExperimentEntry
from src.research.competitor_analyzer import CompetitorAnalyzer
from src.research.pattern_taxonomy import PatternTaxonomy
from src.research.reference_analyzer import ReferenceAnalyzer

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Pipeline:
    """Orchestrates the full generate → evaluate → iterate → route pipeline."""

    def __init__(self, client: GeminiClient | None = None, output_dir: Path | None = None):
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
        self._output_dir = output_dir or PROJECT_ROOT / "output"

    def run_single_brief(self, brief: Brief) -> list[AdRecord]:
        """Process a single brief: enrich → generate 3 variants → evaluate → iterate."""
        enriched = self._interpreter.interpret(brief)
        approaches = self._strategy.select_approaches(enriched)

        records = []
        for i, approach in enumerate(approaches):
            try:
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
            except Exception as e:
                # Single ad failure doesn't crash the batch
                print(f"  Variant {i + 1}/{len(approaches)}: ERROR — {e}")
                error_record = AdRecord(
                    id=f"{brief.id}-v{i}-error",
                    brief_id=brief.id,
                    variant_index=i,
                    ad_copy=_placeholder_ad(),
                    status="failed",
                    error_message=str(e),
                )
                records.append(error_record)

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

    def run_batch(
        self,
        briefs: list[Brief] | None = None,
        count: int | None = None,
    ) -> list[AdRecord]:
        """Run the pipeline for a batch of briefs.

        Args:
            briefs: Explicit list of briefs. If None, loads from config.
            count: Max number of ads to generate. If None, processes all briefs.
        """
        if briefs is None:
            briefs = self._interpreter.load_briefs()

        # If count is set, limit the number of briefs processed
        # Each brief produces ~3 variants, so divide accordingly
        if count is not None:
            max_briefs = max(1, (count + 2) // 3)
            briefs = briefs[:max_briefs]

        all_records = []
        total_briefs = len(briefs)
        for i, brief in enumerate(briefs):
            approved_so_far = sum(1 for r in all_records if r.status == "approved")
            print(
                f"\nBrief {i + 1}/{total_briefs}: {brief.id}  "
                f"[{len(all_records)} ads, {approved_so_far} approved]"
            )
            records = self.run_single_brief(brief)
            all_records.extend(records)

        self.save_results(all_records)
        self._print_summary(all_records)
        return all_records

    def save_results(self, records: list[AdRecord]) -> None:
        """Save approved and failed ads to output JSON files."""
        self._output_dir.mkdir(parents=True, exist_ok=True)

        approved = [r.model_dump(mode="json") for r in records if r.status == "approved"]
        failed = [r.model_dump(mode="json") for r in records if r.status != "approved"]

        with open(self._output_dir / "ad_library.json", "w") as f:
            json.dump(approved, f, indent=2, default=str)

        with open(self._output_dir / "failed_ads.json", "w") as f:
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
        errors = sum(1 for r in records if r.error_message)

        print(f"\n{'=' * 50}")
        print("PIPELINE SUMMARY")
        print(f"{'=' * 50}")
        print(f"Total ads:     {total}")
        if total:
            print(f"Approved:      {approved} ({approved / total * 100:.0f}%)")
        print(f"Failed:        {failed}")
        if errors:
            print(f"Errors:        {errors}")
        print(f"Avg score:     {avg_score:.2f}")
        print(f"Edited:        {edited} ads entered iteration loop")
        print(f"Rescued:       {rescued} ads saved by editing")
        print(f"Total cost:    ${total_cost:.4f}")
        print(f"{'=' * 50}")

    def run_cycles(self, num_cycles: int = 1, count: int | None = None) -> list[AdRecord]:
        """Run the pipeline for multiple cycles with analytics.

        Each cycle processes all briefs. After each cycle:
        - Track quality trends
        - Check for regressions → self-heal
        - Check quality ratchet
        - Log experiment
        - Generate charts after all cycles
        """
        briefs = self._interpreter.load_briefs()
        if count is not None:
            max_briefs = max(1, (count + 2) // 3)
            briefs = briefs[:max_briefs]

        all_records: list[AdRecord] = []

        quality_tracker = QualityTracker()
        token_tracker = TokenTracker()
        ratchet = QualityRatchet(self._gate._threshold)
        healer = SelfHealer(self._client)
        logger = ExperimentLogger()

        for cycle in range(1, num_cycles + 1):
            print(f"\n{'=' * 50}")
            print(f"CYCLE {cycle}/{num_cycles}")
            print(f"{'=' * 50}")

            cycle_records = []
            for i, brief in enumerate(briefs):
                approved_so_far = sum(1 for r in all_records if r.status == "approved")
                approved_cycle = sum(1 for r in cycle_records if r.status == "approved")
                print(
                    f"\n  Brief {i + 1}/{len(briefs)}: {brief.id}  "
                    f"[cycle: {len(cycle_records)} ads, {approved_cycle} approved | "
                    f"total: {len(all_records)} ads, {approved_so_far} approved]"
                )
                records = self.run_single_brief(brief)
                for r in records:
                    r.cycle = cycle
                cycle_records.extend(records)

            all_records.extend(cycle_records)
            self.save_results(all_records)

            # Analytics
            trends = quality_tracker.track(all_records)
            cost_summary = token_tracker.summarize(
                all_records, self._client.usage_log,
            )

            # Check regressions
            regressions = quality_tracker.detect_regressions(trends)
            if regressions:
                print(f"\n  Regressions detected in cycle {cycle}:")
                for reg in regressions:
                    print(
                        f"    {reg['dimension']}: "
                        f"{reg['previous_avg']:.2f} -> "
                        f"{reg['current_avg']:.2f} "
                        f"(drop: {reg['drop']:.2f})"
                    )
                heal_results = healer.heal(regressions, cycle_records)
                for h in heal_results:
                    print(f"    Fix for {h['dimension']}: {h['fix'][:80]}...")

            # Check ratchet
            new_threshold, did_ratchet = ratchet.check_ratchet(trends)
            if did_ratchet:
                self._gate._threshold = new_threshold
                print(
                    f"\n  Quality ratchet raised threshold to {new_threshold:.1f}"
                )

            # Log experiment
            cycle_trends = trends.get("per_cycle", {}).get(cycle, {})
            entry = ExperimentEntry(
                id=f"cycle-{cycle}",
                hypothesis=f"Cycle {cycle} generation with threshold {ratchet.threshold:.1f}",
                change=f"Cycle {cycle} of {num_cycles}",
                result=(
                    f"Score: {cycle_trends.get('avg_score', 0):.2f}, "
                    f"Approved: {cycle_trends.get('approved', 0)}/{cycle_trends.get('count', 0)}"
                ),
                metrics_after={
                    "avg_score": cycle_trends.get("avg_score", 0),
                    "pass_rate": trends.get("pass_rate", 0),
                    "total_cost": cost_summary.get("total_cost", 0),
                    "quality_per_dollar": cost_summary.get("quality_per_dollar", 0),
                },
            )
            logger.log_experiment(entry)

            self._print_summary(cycle_records)

        # Generate charts after all cycles
        trends = quality_tracker.track(all_records)
        cost_summary = token_tracker.summarize(
            all_records, self._client.usage_log,
        )
        quality_tracker.plot_trends(trends)
        token_tracker.plot_cost_dashboard(cost_summary)
        print("\nCharts saved to output/quality_trends.png and output/cost_dashboard.png")
        print(f"Experiment log: {logger.summary()}")

        return all_records

    def run_research(self) -> dict:
        """Run competitive intelligence: analyze competitor + reference ads, build taxonomy."""
        print("\n" + "=" * 50)
        print("COMPETITIVE INTELLIGENCE RESEARCH")
        print("=" * 50)

        # Analyze competitor ads
        print("\nAnalyzing competitor ads...")
        competitor_analyzer = CompetitorAnalyzer(self._client)
        analyses, comp_usage = competitor_analyzer.analyze_batch()
        print(f"  Analyzed {len(analyses)} competitor ads (${comp_usage.cost_usd:.4f})")

        # Extract top patterns
        top_patterns = CompetitorAnalyzer.extract_top_patterns(analyses)
        print(f"  Extracted {len(top_patterns)} hook patterns")
        for p in top_patterns[:5]:
            print(f"    {p['type']}: {p['count']}x (effectiveness: {p['effectiveness_rate']:.0%})")

        # Analyze reference ads
        print("\nAnalyzing reference ad performance correlations...")
        ref_analyzer = ReferenceAnalyzer(self._client)
        ref_patterns, ref_usage = ref_analyzer.analyze_performance_correlations()
        print(f"  Found {len(ref_patterns.get('winning_patterns', []))} winning patterns")
        print(f"  Found {len(ref_patterns.get('losing_patterns', []))} anti-patterns")

        # Build and save taxonomy
        taxonomy = PatternTaxonomy.build(top_patterns, ref_patterns)
        PatternTaxonomy.save(taxonomy)
        print("\nTaxonomy saved to data/patterns/taxonomy.json")

        total_cost = comp_usage.cost_usd + ref_usage.cost_usd
        print(f"Research cost: ${total_cost:.4f}")
        print("=" * 50)

        return taxonomy


def _placeholder_ad():
    """Return a placeholder AdCopy for error records."""
    from src.models import AdCopy
    return AdCopy(
        primary_text="[Generation failed]",
        headline="Error",
        description="This ad failed to generate.",
        cta="Learn More",
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Nerdy Ad Engine — autonomous ad copy generation pipeline"
    )
    parser.add_argument(
        "--count", type=int, default=None,
        help="Maximum number of ads to generate (default: all briefs × 3 variants)",
    )
    parser.add_argument(
        "--cycles", type=int, default=1,
        help="Number of generation cycles (default: 1)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run in demo mode (quick walkthrough)",
    )
    parser.add_argument(
        "--research", action="store_true",
        help="Run competitive intelligence research",
    )
    parser.add_argument(
        "--port", type=int, default=8020,
        help="Server port for dashboard (default: 8020, range: 8020-8030)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = _parse_args(argv)

    # Validate port range
    if not (8020 <= args.port <= 8030):
        print(f"Error: port must be in range 8020-8030, got {args.port}")
        sys.exit(1)

    # Deterministic seeding
    random.seed(args.seed)

    # Output directory
    output_dir = Path(args.output_dir) if args.output_dir else None
    pipeline = Pipeline(output_dir=output_dir)

    if args.demo:
        from src.demo import run_demo
        run_demo(pipeline, port=args.port)
    elif args.research:
        pipeline.run_research()
    elif args.cycles > 1:
        pipeline.run_cycles(args.cycles, count=args.count)
    else:
        pipeline.run_batch(count=args.count)


if __name__ == "__main__":
    main()
