"""Variant strategy — selects diverse hook/angle combinations for each brief.

No LLM calls. Pure strategy logic ensuring 3 variants per brief use
genuinely different approaches. Optionally informed by competitive intelligence taxonomy.
"""

from src.models import Brief

# Each approach is a (hook_type, angle, instruction) tuple
APPROACHES = [
    {
        "hook_type": "question",
        "angle": "parent_anxiety",
        "instruction": (
            "Open with a question that taps into parent anxiety about their child's "
            "college readiness. Use a conversational, empathetic tone."
        ),
    },
    {
        "hook_type": "statistic",
        "angle": "social_proof",
        "instruction": (
            "Lead with a compelling statistic about score improvements or student success. "
            "Use numbers to build credibility and trust."
        ),
    },
    {
        "hook_type": "story",
        "angle": "aspiration",
        "instruction": (
            "Start with a brief relatable scenario or student journey. Paint a picture of "
            "what success looks like after working with a tutor."
        ),
    },
    {
        "hook_type": "empathy",
        "angle": "stress_relief",
        "instruction": (
            "Acknowledge the reader's stress or overwhelm directly. Position the product as "
            "the solution that removes that burden."
        ),
    },
    {
        "hook_type": "comparison",
        "angle": "differentiation",
        "instruction": (
            "Contrast personalized 1-on-1 tutoring against generic alternatives (big classes, "
            "apps, self-study). Highlight what makes this approach different."
        ),
    },
    {
        "hook_type": "urgency",
        "angle": "timeliness",
        "instruction": (
            "Create time-based motivation (upcoming test dates, limited spots, seasonal prep). "
            "Keep urgency supportive, not fear-based."
        ),
    },
    {
        "hook_type": "authority",
        "angle": "expertise",
        "instruction": (
            "Lead with tutor expertise and credentials. Emphasize the quality and selectivity "
            "of the tutoring network."
        ),
    },
    {
        "hook_type": "value",
        "angle": "investment",
        "instruction": (
            "Frame tutoring as a smart investment with clear ROI. Mention free trial or "
            "consultation to lower the perceived risk."
        ),
    },
]

# Audience-to-preferred-angles mapping
AUDIENCE_PREFERENCES = {
    "parents_anxious": ["parent_anxiety", "stress_relief", "social_proof", "investment"],
    "students_stressed": ["stress_relief", "aspiration", "social_proof", "empathy"],
    "families_comparing": ["differentiation", "investment", "social_proof", "expertise"],
}


class VariantStrategy:
    """Selects maximally diverse approach combinations for ad variants."""

    def select_approaches(self, brief: Brief, count: int = 3) -> list[str]:
        """Select `count` diverse variant instructions for a given brief.

        Prioritizes approaches relevant to the audience, ensures no duplicate hook types.
        """
        audience = brief.audience_segment
        preferred_angles = AUDIENCE_PREFERENCES.get(audience, [])

        # Sort approaches: preferred angles first, then remaining
        scored = []
        for i, approach in enumerate(APPROACHES):
            priority = 0
            if approach["angle"] in preferred_angles:
                priority = len(preferred_angles) - preferred_angles.index(approach["angle"])
            scored.append((priority, i, approach))

        scored.sort(key=lambda x: (-x[0], x[1]))

        # Pick top `count` with unique hook types
        selected = []
        used_hooks = set()
        for _, _, approach in scored:
            if approach["hook_type"] not in used_hooks:
                selected.append(approach["instruction"])
                used_hooks.add(approach["hook_type"])
            if len(selected) >= count:
                break

        return selected

    def select_from_taxonomy(
        self, taxonomy: dict, brief: Brief, count: int = 3,
    ) -> list[str]:
        """Select approaches biased toward high-effectiveness patterns from taxonomy.

        Falls back to default select_approaches if taxonomy is empty or has no hooks.
        """
        hooks = taxonomy.get("hooks", [])
        if not hooks:
            return self.select_approaches(brief, count)

        # Sort taxonomy hooks by effectiveness_rate descending
        ranked_hooks = sorted(
            hooks,
            key=lambda h: h.get("effectiveness_rate", 0.0),
            reverse=True,
        )

        # Map taxonomy hook types to our APPROACHES
        hook_to_approach = {a["hook_type"]: a for a in APPROACHES}

        selected = []
        used_hooks = set()
        for hook_entry in ranked_hooks:
            hook_type = hook_entry.get("type", "")
            if hook_type in hook_to_approach and hook_type not in used_hooks:
                selected.append(hook_to_approach[hook_type]["instruction"])
                used_hooks.add(hook_type)
            if len(selected) >= count:
                break

        # Fill remaining slots from default strategy if taxonomy didn't provide enough
        if len(selected) < count:
            defaults = self.select_approaches(brief, count)
            for instruction in defaults:
                if instruction not in selected:
                    selected.append(instruction)
                if len(selected) >= count:
                    break

        return selected
