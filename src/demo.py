"""Demo mode — 3-5 minute walkthrough of the Nerdy Ad Engine pipeline."""

import json
from pathlib import Path

from src.models import Brief

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_demo(pipeline, port: int = 8020) -> None:
    """Run a compact demo showcasing the full pipeline.

    Steps:
    1. Calibration check — show evaluator alignment
    2. Single brief pipeline — generate → evaluate → iterate
    3. Quality trends — show dimension averages
    4. Cost dashboard — show cost breakdown
    5. Top ads — display best-scoring approved ads
    """
    print("\n" + "=" * 60)
    print("  NERDY AD ENGINE — DEMO MODE")
    print("=" * 60)

    # ── Step 1: Calibration check ──────────────────────────────
    print("\n[1/5] EVALUATOR CALIBRATION")
    print("-" * 40)
    cal_path = PROJECT_ROOT / "output" / "calibration_report.json"
    if cal_path.exists():
        with open(cal_path) as f:
            cal = json.load(f)
        total = len(cal) if isinstance(cal, list) else cal.get("total", "?")
        aligned = (
            sum(1 for r in cal if r.get("alignment") == "aligned")
            if isinstance(cal, list)
            else cal.get("aligned", "?")
        )
        print(f"  Calibration report found: {aligned}/{total} aligned")
    else:
        print("  No calibration report found — run calibration first.")
        print("  Continuing with demo...")

    # ── Step 2: Single brief pipeline ──────────────────────────
    print("\n[2/5] SINGLE BRIEF PIPELINE")
    print("-" * 40)
    demo_brief = Brief(
        id="demo-brief-01",
        audience_segment="parents_anxious",
        product="SAT Test Prep",
        campaign_goal="conversion",
        key_message="Raise your SAT score 200+ points with personalized tutoring",
    )
    print(f"  Brief: {demo_brief.id}")
    print(f"  Audience: {demo_brief.audience_segment}")
    print(f"  Goal: {demo_brief.campaign_goal}")
    print()

    records = pipeline.run_single_brief(demo_brief)

    # ── Step 3: Quality summary ────────────────────────────────
    print("\n[3/5] QUALITY SUMMARY")
    print("-" * 40)
    for r in records:
        status = r.status.upper()
        score = r.evaluation.aggregate_score if r.evaluation else 0
        edits = len(r.iteration_history) - 1 if r.iteration_history else 0
        print(f"  {r.id}: score={score:.2f} [{status}] ({edits} edits)")
        if r.evaluation:
            for ds in r.evaluation.dimension_scores:
                bar = "#" * int(ds.score)
                print(f"    {ds.dimension:25s} {ds.score:4.1f} {bar}")

    # ── Step 4: Cost breakdown ─────────────────────────────────
    print("\n[4/5] COST BREAKDOWN")
    print("-" * 40)
    total_cost = sum(r.total_cost_usd for r in records)
    gen_cost = sum(r.generation_cost_usd for r in records)
    eval_cost = sum(r.evaluation_cost_usd for r in records)
    print(f"  Generation:  ${gen_cost:.4f}")
    print(f"  Evaluation:  ${eval_cost:.4f}")
    print(f"  Total:       ${total_cost:.4f}")
    approved = [r for r in records if r.status == "approved"]
    if approved:
        cost_per_approved = total_cost / len(approved)
        print(f"  Per approved: ${cost_per_approved:.4f}")

    # ── Step 5: Top ads ────────────────────────────────────────
    print("\n[5/5] TOP ADS")
    print("-" * 40)
    sorted_records = sorted(
        [r for r in records if r.evaluation],
        key=lambda r: r.evaluation.aggregate_score,
        reverse=True,
    )
    for r in sorted_records[:3]:
        print(f"\n  [{r.evaluation.aggregate_score:.2f}] {r.id}")
        print(f"  Headline:    {r.ad_copy.headline}")
        print(f"  Primary:     {r.ad_copy.primary_text[:120]}...")
        print(f"  Description: {r.ad_copy.description}")
        print(f"  CTA:         {r.ad_copy.cta}")

    # ── Done ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  DEMO COMPLETE")
    print(f"  Generated {len(records)} ads, {len(approved)} approved")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"  Dashboard port: {port} (if serving)")
    print("=" * 60)
