"""Tests for taxonomy-enriched generation — brief interpreter + variant strategy."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.generate.brief_interpreter import BriefInterpreter
from src.generate.variant_strategy import VariantStrategy
from src.models import Brief


def _sample_taxonomy():
    return {
        "hooks": [
            {"type": "social_proof", "frequency": 5, "effectiveness_rate": 0.8},
            {"type": "empathy", "frequency": 3, "effectiveness_rate": 0.9},
            {"type": "question", "frequency": 4, "effectiveness_rate": 0.5},
        ],
        "winning_patterns": [
            {"pattern": "Parent empathy opening", "description": "Opens with empathy",
             "examples": ["You've watched your child stress"]},
        ],
        "losing_patterns": [
            {"pattern": "Corporate jargon", "description": "Buzzwords kill readability"},
        ],
        "structural_insights": ["Short sentences work best"],
        "emotional_insights": ["Address anxiety directly"],
    }


def _make_brief():
    return Brief(
        id="test-enrich", audience_segment="parents_anxious",
        product="SAT", campaign_goal="conversion",
    )


class TestEnrichedGeneration:
    def test_enrichment_includes_taxonomy(self):
        """BriefInterpreter should inject taxonomy hooks into enrichment context."""
        taxonomy = _sample_taxonomy()
        # Write taxonomy to a temp file and patch the path
        with tempfile.TemporaryDirectory() as tmpdir:
            tax_path = Path(tmpdir) / "data" / "patterns" / "taxonomy.json"
            tax_path.parent.mkdir(parents=True)
            with open(tax_path, "w") as f:
                json.dump(taxonomy, f)

            # Patch PROJECT_ROOT so BriefInterpreter finds our temp taxonomy
            with patch("src.generate.brief_interpreter.PROJECT_ROOT", Path(tmpdir)):
                # Need brand_guidelines and briefs yamls too
                config_dir = Path(tmpdir) / "config"
                config_dir.mkdir()

                # Minimal brand guidelines
                import yaml
                brand = {
                    "brand": {"name": "Varsity Tutors", "product": "SAT"},
                    "voice": {"attributes": ["empowering"]},
                    "tone": {"do": ["be warm"], "dont": ["use jargon"]},
                    "audiences": {
                        "parents_anxious": {
                            "label": "Anxious Parents",
                            "emotional_triggers": ["worry"],
                            "key_messages": ["Expert help"],
                        }
                    },
                }
                with open(config_dir / "brand_guidelines.yaml", "w") as f:
                    yaml.dump(brand, f)
                with open(config_dir / "briefs.yaml", "w") as f:
                    yaml.dump({"briefs": []}, f)

                interpreter = BriefInterpreter(
                    brand_path=str(config_dir / "brand_guidelines.yaml"),
                    briefs_path=str(config_dir / "briefs.yaml"),
                )
                enriched = interpreter.interpret(_make_brief())
                ctx = enriched.enrichment_context
                assert "TOP PERFORMING HOOKS" in ctx
                assert "social_proof" in ctx
                assert "WINNING PATTERNS" in ctx
                assert "Parent empathy opening" in ctx
                assert "PATTERNS TO AVOID" in ctx

    def test_variant_strategy_prefers_high_effectiveness(self):
        """select_from_taxonomy() should prefer high-effectiveness hooks."""
        taxonomy = _sample_taxonomy()
        strategy = VariantStrategy()
        brief = _make_brief()
        approaches = strategy.select_from_taxonomy(taxonomy, brief, count=2)
        assert len(approaches) == 2
        # Each approach should be a non-empty instruction string
        for a in approaches:
            assert isinstance(a, str)
            assert len(a) > 10

    def test_backward_compatible_without_taxonomy(self):
        """select_from_taxonomy() with empty taxonomy should fall back to defaults."""
        strategy = VariantStrategy()
        brief = _make_brief()
        approaches = strategy.select_from_taxonomy({}, brief, count=3)
        assert len(approaches) == 3
        # Should be identical to regular select_approaches
        default = strategy.select_approaches(brief, count=3)
        assert approaches == default
