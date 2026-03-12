"""Brief interpreter — enriches minimal briefs with brand context and audience triggers.

No LLM calls. Pure config-driven string assembly (zero cost, auditable).
"""

from pathlib import Path

import yaml

from src.models import Brief

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class BriefInterpreter:
    """Enriches briefs with brand guidelines, audience triggers, and product context."""

    def __init__(
        self,
        brand_path: str | None = None,
        briefs_path: str | None = None,
    ):
        if brand_path is None:
            brand_path = str(PROJECT_ROOT / "config" / "brand_guidelines.yaml")
        if briefs_path is None:
            briefs_path = str(PROJECT_ROOT / "config" / "briefs.yaml")

        with open(brand_path) as f:
            self._brand = yaml.safe_load(f)
        with open(briefs_path) as f:
            self._briefs_config = yaml.safe_load(f)

        # Try to load taxonomy if available (Phase 4)
        taxonomy_path = PROJECT_ROOT / "data" / "patterns" / "taxonomy.json"
        self._taxonomy = None
        if taxonomy_path.exists():
            import json

            with open(taxonomy_path) as f:
                data = json.load(f)
                if data:  # non-empty
                    self._taxonomy = data

    def interpret(self, brief: Brief) -> Brief:
        """Enrich a brief with brand voice, audience triggers, and product context."""
        sections = []

        # Brand voice
        brand = self._brand.get("brand", {})
        voice = self._brand.get("voice", {})
        tone = self._brand.get("tone", {})

        sections.append(f"BRAND: {brand.get('name', 'Varsity Tutors')}")
        sections.append(f"PRODUCT: {brand.get('product', brief.product)}")

        voice_attrs = voice.get("attributes", [])
        if voice_attrs:
            sections.append(f"VOICE: {', '.join(voice_attrs)}")

        tone_dos = tone.get("do", [])
        if tone_dos:
            sections.append("TONE DO: " + " | ".join(tone_dos))

        tone_donts = tone.get("dont", [])
        if tone_donts:
            sections.append("TONE DON'T: " + " | ".join(tone_donts))

        # Audience-specific context
        audiences = self._brand.get("audiences", {})
        audience_data = audiences.get(brief.audience_segment, {})
        if audience_data:
            label = audience_data.get("label", brief.audience_segment)
            sections.append(f"TARGET AUDIENCE: {label}")

            triggers = audience_data.get("emotional_triggers", [])
            if triggers:
                sections.append("EMOTIONAL TRIGGERS: " + ", ".join(triggers))

            messages = audience_data.get("key_messages", [])
            if messages:
                sections.append("KEY MESSAGES: " + " | ".join(messages))

        # Brief-specific overrides
        if brief.key_message:
            sections.append(f"PRIMARY MESSAGE: {brief.key_message}")
        if brief.tone_override:
            sections.append(f"TONE OVERRIDE: {brief.tone_override}")

        sections.append(f"CAMPAIGN GOAL: {brief.campaign_goal}")

        # Ad format constraints
        ad_format = self._brand.get("ad_format", {})
        if ad_format:
            sections.append("FORMAT CONSTRAINTS:")
            for field_name, field_cfg in ad_format.items():
                if isinstance(field_cfg, dict):
                    max_chars = field_cfg.get("max_chars", "")
                    if max_chars:
                        sections.append(f"  {field_name}: max {max_chars} chars")
                    allowed = field_cfg.get("allowed_values", [])
                    if allowed:
                        sections.append(f"  {field_name}: one of {allowed}")

        # Inject taxonomy patterns if available (Phase 4)
        if self._taxonomy:
            hooks = self._taxonomy.get("hooks", [])
            if hooks:
                top_hooks = [
                    h.get("type", "") for h in hooks[:5] if isinstance(h, dict)
                ]
                if top_hooks:
                    sections.append(
                        f"TOP PERFORMING HOOKS: {', '.join(top_hooks)}"
                    )

            winning = self._taxonomy.get("winning_patterns", [])
            if winning:
                win_names = [
                    w.get("pattern", "") for w in winning[:3] if isinstance(w, dict)
                ]
                if win_names:
                    sections.append(
                        f"WINNING PATTERNS: {', '.join(win_names)}"
                    )

            losing = self._taxonomy.get("losing_patterns", [])
            if losing:
                lose_names = [
                    lp.get("pattern", "") for lp in losing[:3] if isinstance(lp, dict)
                ]
                if lose_names:
                    sections.append(
                        f"PATTERNS TO AVOID: {', '.join(lose_names)}"
                    )

        enrichment = "\n".join(sections)

        return brief.model_copy(update={"enrichment_context": enrichment})

    def load_briefs(self) -> list[Brief]:
        """Parse briefs.yaml into a list of Brief objects."""
        raw_briefs = self._briefs_config.get("briefs", [])
        briefs = []
        for raw in raw_briefs:
            brief = Brief(
                id=raw["id"],
                audience_segment=raw["audience_segment"],
                product=raw["product"],
                campaign_goal=raw["campaign_goal"],
                tone_override=raw.get("tone_override"),
                key_message=raw.get("key_message"),
            )
            briefs.append(brief)
        return briefs
