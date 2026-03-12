"""Tests for PatternTaxonomy — build, save, and load pattern taxonomy."""

import tempfile
from pathlib import Path

from src.research.pattern_taxonomy import PatternTaxonomy


def _sample_competitor_patterns():
    return [
        {"type": "social_proof", "count": 5, "effectiveness_rate": 0.8},
        {"type": "question", "count": 3, "effectiveness_rate": 0.67},
        {"type": "urgency", "count": 2, "effectiveness_rate": 0.5},
    ]


def _sample_reference_patterns():
    return {
        "winning_patterns": [
            {"pattern": "Parent empathy", "description": "Opens with empathy",
             "examples": ["You've watched your child stress"]},
        ],
        "losing_patterns": [
            {"pattern": "Corporate jargon", "description": "Buzzwords kill readability"},
        ],
        "structural_insights": ["Short sentences before value prop"],
        "emotional_insights": ["Address anxiety directly"],
    }


class TestPatternTaxonomy:
    def test_build_merges_patterns(self):
        """build() should merge competitor and reference patterns into a taxonomy."""
        taxonomy = PatternTaxonomy.build(
            _sample_competitor_patterns(), _sample_reference_patterns(),
        )
        assert "hooks" in taxonomy
        assert "winning_patterns" in taxonomy
        assert "losing_patterns" in taxonomy
        assert len(taxonomy["hooks"]) == 3
        assert taxonomy["hooks"][0]["type"] == "social_proof"

    def test_save_load_roundtrip(self):
        """save() then load() should produce the same taxonomy."""
        taxonomy = PatternTaxonomy.build(
            _sample_competitor_patterns(), _sample_reference_patterns(),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "taxonomy.json"
            PatternTaxonomy.save(taxonomy, path)
            loaded = PatternTaxonomy.load(path)
            assert loaded == taxonomy

    def test_expected_structure(self):
        """Taxonomy should have the 5 expected top-level keys."""
        taxonomy = PatternTaxonomy.build(
            _sample_competitor_patterns(), _sample_reference_patterns(),
        )
        expected_keys = {"hooks", "winning_patterns", "losing_patterns",
                         "structural_insights", "emotional_insights"}
        assert set(taxonomy.keys()) == expected_keys

    def test_empty_inputs(self):
        """build() should handle empty inputs gracefully."""
        taxonomy = PatternTaxonomy.build([], {})
        assert taxonomy["hooks"] == []
        assert taxonomy["winning_patterns"] == []
        assert taxonomy["losing_patterns"] == []
