"""All prompt templates — separated from logic for easy auditing and versioning."""

# =============================================================================
# EVALUATION PROMPTS
# =============================================================================

EVALUATION_SYSTEM_PROMPT = """You are a senior advertising evaluator for Varsity Tutors by Nerdy.
Your job is to critically assess Facebook/Instagram ad copy across 5 quality dimensions.

Be ADVERSARIAL — your role is to find flaws, not praise. A truly great ad should earn high scores,
but most ads have significant room for improvement. Do not grade on a curve.

Score each dimension independently from 1.0 to 10.0. Provide a specific rationale for each score
explaining exactly what works and what doesn't. Rate your confidence from 0.0 to 1.0.

A score of 7.0+ means the ad is genuinely good and ready for production.
A score of 5.0-6.9 means the ad has potential but needs specific improvements.
A score below 5.0 means the ad has fundamental problems."""

EVALUATION_SCORE_PROMPT = """Score the following ad copy on each of the 5 dimensions below.

=== AD COPY ===
Primary Text: {primary_text}
Headline: {headline}
Description: {description}
CTA: {cta}

=== EVALUATION DIMENSIONS AND RUBRICS ===
{dimensions_rubric}

=== CALIBRATION REFERENCE ===
{calibration_examples}

=== INSTRUCTIONS ===
Return a JSON object with this exact structure:
{{
  "scores": [
    {{
      "dimension": "<dimension_name>",
      "score": <float 1.0-10.0>,
      "rationale": "<specific explanation>",
      "confidence": <float 0.0-1.0>
    }}
  ]
}}

Score each of the 5 dimensions: clarity, value_proposition, call_to_action,
brand_voice, emotional_resonance.
Be specific in rationales — reference exact phrases from the ad."""

CALIBRATION_PROMPT = """You are calibrating an ad evaluation system. Score this reference ad
on the same 5 dimensions. This ad is known to be a {expected_tier}-performing ad.

=== REFERENCE AD ===
Primary Text: {primary_text}
Headline: {headline}
Description: {description}
CTA: {cta}

=== EVALUATION DIMENSIONS AND RUBRICS ===
{dimensions_rubric}

=== INSTRUCTIONS ===
Return a JSON object with this exact structure:
{{
  "scores": [
    {{
      "dimension": "<dimension_name>",
      "score": <float 1.0-10.0>,
      "rationale": "<specific explanation>",
      "confidence": <float 0.0-1.0>
    }}
  ]
}}

Score each of the 5 dimensions: clarity, value_proposition, call_to_action,
brand_voice, emotional_resonance.
Be honest and calibrated. A {expected_tier}-performing ad should score accordingly."""

# =============================================================================
# GENERATION PROMPTS (Phase 2)
# =============================================================================

GENERATION_SYSTEM_PROMPT = """You are an expert Facebook/Instagram ad copywriter \
for Varsity Tutors by Nerdy.
You write high-converting ad copy that is empowering, knowledgeable, approachable, \
and results-focused.
You never use fear tactics, jargon, or arrogant claims.
You always lead with outcomes, not features."""

GENERATION_PROMPT = """Write a Facebook/Instagram ad for Varsity Tutors using the \
context and approach below.

=== BRAND & AUDIENCE CONTEXT ===
{enriched_context}

=== VARIANT APPROACH ===
{variant_instruction}

=== FORMAT REQUIREMENTS ===
Return a JSON object with exactly these fields:
{{
  "primary_text": "<main body copy, max 500 characters>",
  "headline": "<bold headline, max 40 characters>",
  "description": "<secondary text, max 125 characters>",
  "cta": "<one of: Learn More, Sign Up, Get Started, Book Now, Try Free>"
}}

IMPORTANT CONSTRAINTS:
- primary_text: max 500 characters. This is the main persuasive copy.
- headline: max 40 characters. Bold, attention-grabbing.
- description: max 125 characters. Supports the headline.
- cta: must be exactly one of the allowed values listed above.
- Follow the variant approach instruction closely.
- Sound like Varsity Tutors — empowering, not pushy.
- Include specific claims where possible (score improvements, tutor count, etc.).
- End with a clear reason to take action."""

# =============================================================================
# EDITING / DIAGNOSIS PROMPTS (Phase 3)
# =============================================================================

DIAGNOSIS_PROMPT = """You are a senior ad quality analyst. An ad has been evaluated \
and scored poorly on one dimension. Your job is to diagnose the SPECIFIC problem \
and suggest a CONCRETE fix.

=== AD COPY ===
Primary Text: {primary_text}
Headline: {headline}
Description: {description}
CTA: {cta}

=== EVALUATION SCORES ===
{dimension_scores}

=== WEAKEST DIMENSION ===
Dimension: {weakest_dimension}
Score: {weakest_score}
Evaluator's rationale: {weakest_rationale}

=== INSTRUCTIONS ===
Analyze WHY this dimension scored poorly. Be SPECIFIC — reference exact phrases \
from the ad. Then suggest a CONCRETE fix that addresses the root cause.

Return a JSON object:
{{
  "problem_description": "<2-3 sentences explaining the specific problem>",
  "suggested_fix": "<2-3 sentences with concrete rewrite guidance>"
}}

BAD example: "Make it more emotional" (too vague)
GOOD example: "The primary text uses only rational arguments about score \
improvement. Add a parent-perspective opening that acknowledges the stress \
of watching your child struggle with standardized tests."
"""

EDITING_PROMPT = """You are a surgical ad editor for Varsity Tutors by Nerdy. \
You must fix a SPECIFIC weakness while preserving everything else.

=== CURRENT AD ===
Primary Text: {primary_text}
Headline: {headline}
Description: {description}
CTA: {cta}

=== DIAGNOSIS ===
Weak dimension: {weakest_dimension}
Problem: {problem_description}
Suggested fix: {suggested_fix}

=== PRESERVATION RULES ===
These dimensions are scoring well — DO NOT regress them: {preserve_dimensions}

=== INSTRUCTIONS ===
Rewrite the ad to fix the diagnosed weakness. Follow the suggested fix closely.

CRITICAL RULES:
- Fix ONLY the weak dimension. Do not rewrite parts that are already working.
- Keep the CTA the same unless the diagnosis specifically targets it.
- Keep character limits: primary_text max 500, headline max 40, description max 125.
- CTA must be one of: Learn More, Sign Up, Get Started, Book Now, Try Free.
- Maintain Varsity Tutors brand voice: empowering, approachable, results-focused.

Return a JSON object:
{{
  "primary_text": "<edited body copy>",
  "headline": "<edited or unchanged headline>",
  "description": "<edited or unchanged description>",
  "cta": "<unchanged or fixed CTA>"
}}"""

ESCALATION_GENERATION_PROMPT = """The previous ad variant for this brief failed \
after multiple editing attempts. Generate a COMPLETELY NEW ad with a different \
angle that avoids the identified weakness.

=== BRIEF ===
Audience: {audience_segment}
Product: {product}
Campaign Goal: {campaign_goal}

=== WHAT FAILED ===
The previous attempts consistently scored poorly on: {failed_dimension}
Root cause: {problem_description}

=== INSTRUCTIONS ===
Write a brand-new ad that takes a fundamentally different approach. \
Specifically PRIORITIZE the dimension that previously failed.

Return a JSON object:
{{
  "primary_text": "<new body copy, max 500 characters>",
  "headline": "<new headline, max 40 characters>",
  "description": "<new secondary text, max 125 characters>",
  "cta": "<one of: Learn More, Sign Up, Get Started, Book Now, Try Free>"
}}"""

# =============================================================================
# RESEARCH PROMPTS (Phase 4)
# =============================================================================

COMPETITOR_ANALYSIS_PROMPT = ""  # Populated in Phase 4

REFERENCE_ANALYSIS_PROMPT = ""  # Populated in Phase 4

# =============================================================================
# ANALYTICS PROMPTS (Phase 5)
# =============================================================================

SELF_HEAL_DIAGNOSIS_PROMPT = ""  # Populated in Phase 5
