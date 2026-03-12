"""Competitor ad analyzer — extracts structural patterns from competitor ads."""

import json
from collections import Counter
from pathlib import Path

from src.llm.client import GeminiClient
from src.llm.prompts import COMPETITOR_ANALYSIS_PROMPT
from src.models import LLMUsage

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class CompetitorAnalyzer:
    """Analyzes competitor ads to extract hook types, angles, and structural patterns."""

    def __init__(self, client: GeminiClient, ads_path: str | None = None):
        self._client = client
        if ads_path is None:
            ads_path = str(PROJECT_ROOT / "data" / "competitor_ads.json")
        with open(ads_path) as f:
            self._ads = json.load(f)

    def analyze_ad(self, ad: dict) -> tuple[dict, LLMUsage]:
        """Analyze a single competitor ad and extract structural patterns."""
        prompt = COMPETITOR_ANALYSIS_PROMPT.format(
            source=ad.get("source", "Unknown"),
            primary_text=ad.get("primary_text", ""),
            headline=ad.get("headline", ""),
            description=ad.get("description", ""),
            cta=ad.get("cta", ""),
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

        analysis = json.loads(text)
        analysis["source"] = ad.get("source", "Unknown")
        analysis["ad_id"] = ad.get("id", "")
        return analysis, usage

    def analyze_batch(self) -> tuple[list[dict], LLMUsage]:
        """Analyze all competitor ads. Returns (analyses, combined_usage)."""
        analyses = []
        total_input = 0
        total_output = 0
        total_cost = 0.0
        total_duration = 0.0
        model_name = ""

        for ad in self._ads:
            analysis, usage = self.analyze_ad(ad)
            analyses.append(analysis)
            total_input += usage.input_tokens
            total_output += usage.output_tokens
            total_cost += usage.cost_usd
            total_duration += usage.duration_seconds
            model_name = usage.model

        combined_usage = LLMUsage(
            model=model_name,
            input_tokens=total_input,
            output_tokens=total_output,
            cost_usd=total_cost,
            call_type="research",
            duration_seconds=round(total_duration, 2),
        )
        return analyses, combined_usage

    @staticmethod
    def extract_top_patterns(analyses: list[dict], top_n: int = 10) -> list[dict]:
        """Extract top patterns from analyses by frequency and effectiveness.

        Returns a list of pattern dicts with type, count, and effectiveness_rate.
        """
        if not analyses:
            return []

        # Count hook types
        hook_counts = Counter(a.get("hook_type", "unknown") for a in analyses)

        # Count effectiveness per hook type
        hook_effectiveness: dict[str, list[str]] = {}
        for a in analyses:
            hook = a.get("hook_type", "unknown")
            eff = a.get("estimated_effectiveness", "medium")
            hook_effectiveness.setdefault(hook, []).append(eff)

        # Build pattern list
        patterns = []
        for hook, count in hook_counts.most_common(top_n):
            effs = hook_effectiveness.get(hook, [])
            high_rate = effs.count("high") / len(effs) if effs else 0.0
            patterns.append({
                "type": hook,
                "count": count,
                "effectiveness_rate": round(high_rate, 2),
            })

        return patterns
