"""Pattern taxonomy — merges competitor and reference patterns into a structured taxonomy."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TAXONOMY_PATH = PROJECT_ROOT / "data" / "patterns" / "taxonomy.json"


class PatternTaxonomy:
    """Builds, saves, and loads a structured pattern taxonomy."""

    @staticmethod
    def build(
        competitor_patterns: list[dict],
        reference_patterns: dict,
    ) -> dict:
        """Merge competitor patterns and reference analysis into a taxonomy.

        Args:
            competitor_patterns: Output of CompetitorAnalyzer.extract_top_patterns()
            reference_patterns: Output of ReferenceAnalyzer.analyze_performance_correlations()

        Returns:
            Structured taxonomy with hooks, winning_patterns, losing_patterns, insights.
        """
        # Hooks from competitor analysis
        hooks = []
        for p in competitor_patterns:
            hooks.append({
                "type": p.get("type", "unknown"),
                "frequency": p.get("count", 0),
                "effectiveness_rate": p.get("effectiveness_rate", 0.0),
            })

        # Winning/losing patterns from reference analysis
        winning = reference_patterns.get("winning_patterns", [])
        losing = reference_patterns.get("losing_patterns", [])
        structural = reference_patterns.get("structural_insights", [])
        emotional = reference_patterns.get("emotional_insights", [])

        return {
            "hooks": hooks,
            "winning_patterns": winning,
            "losing_patterns": losing,
            "structural_insights": structural,
            "emotional_insights": emotional,
        }

    @staticmethod
    def save(taxonomy: dict, path: Path | None = None) -> None:
        """Save taxonomy to JSON file."""
        if path is None:
            path = TAXONOMY_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(taxonomy, f, indent=2)

    @staticmethod
    def load(path: Path | None = None) -> dict:
        """Load taxonomy from JSON file. Returns empty dict if not found."""
        if path is None:
            path = TAXONOMY_PATH
        if not path.exists():
            return {}
        with open(path) as f:
            return json.load(f)
