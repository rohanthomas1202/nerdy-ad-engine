# Decision Log — Nerdy Ad Engine

Timestamped engineering decisions, trade-offs, failed experiments, and rationale.

---

## Architecture

### 2026-03-01 — Evaluator-First Architecture

**Decision:** Build and calibrate the quality evaluator (Phase 1) before any ad generation (Phase 2).

**Rationale:** Without a reliable quality signal, generating ads is just "generate and hope." The evaluator is the feedback mechanism that makes iteration possible. If the evaluator can't distinguish good ads from bad ones, nothing downstream works.

**Trade-off:** This means Phase 1 produces zero ads — it only proves that the evaluation pipeline is sound. This felt risky ("what if we run out of time?") but paid off: once calibration hit 80%+ alignment, every subsequent phase had a trustworthy quality signal to build on.

**Alternative considered:** Build generation and evaluation in parallel. Rejected because debugging a bad generator with a bad evaluator is a nightmare — you can't tell which one is wrong.

### 2026-03-01 — Pydantic v2 as Contract Layer

**Decision:** Use Pydantic BaseModel for every data structure passed between modules (AdCopy, Brief, DimensionScore, EvaluationResult, AdRecord, etc.).

**Rationale:** LLM outputs are inherently untyped — raw JSON that could be anything. Pydantic gives us runtime validation at the boundary where LLM output enters our system. If Gemini returns a score of 11.0 or a CTA of "Buy Now," the validator catches it immediately rather than propagating garbage downstream.

**Trade-off:** More boilerplate than plain dicts. Worth it for the safety guarantees and self-documenting code.

### 2026-03-02 — Unified Gemini Client with Token Tracking

**Decision:** Single `GeminiClient` class for all API calls (generation, evaluation, editing, research), with per-call token and cost tracking built in.

**Rationale:** Every LLM call has a cost. If cost tracking is an afterthought, you can't compute quality-per-dollar or detect which pipeline stages are expensive. By baking tracking into the client, every call is automatically metered.

**Trade-off:** The client carries a growing `usage_log` list in memory. For 100-200 ads this is fine; at 10,000+ ads you'd want to flush to disk periodically.

---

## Evaluator Calibration

### 2026-03-01 — 5 Evaluation Dimensions

**Decision:** Evaluate on Clarity, Value Proposition, Call-to-Action, Brand Voice, and Emotional Resonance.

**Rationale:** These map directly to what makes a Facebook ad effective. Clarity and Value Proposition are non-negotiable. CTA drives conversion. Brand Voice ensures consistency. Emotional Resonance is the differentiator between a serviceable ad and one that moves people.

**Alternative considered:** 3 dimensions (simpler) or 7+ (more granular). 5 was the sweet spot — enough specificity for targeted editing in Phase 3, not so many that the evaluator prompt becomes unwieldy.

### 2026-03-01 — Quality Gate at 7.0

**Decision:** Ads scoring ≥ 7.0 aggregate pass; below-threshold ads enter the iteration loop.

**Rationale:** On a 1-10 scale, 7.0 means "genuinely good and ready for production." Below 7.0, the ad has specific, fixable problems. Above 8.0 is excellent. The threshold is intentionally moderate — too high and nothing passes; too low and mediocre ads leak through.

**What we learned:** The quality ratchet (Phase 5) can auto-raise this threshold as the system proves it can consistently generate higher-quality ads.

### 2026-03-02 — Adversarial Evaluation Prompt

**Decision:** The evaluation system prompt instructs the LLM to be "ADVERSARIAL — your role is to find flaws, not praise."

**Rationale:** LLMs have a well-documented tendency toward positive bias. Without explicit adversarial framing, early evaluations were clustered at 8-9 regardless of actual quality. The adversarial prompt produces more discriminating, useful scores.

**Failed experiment:** Initially tried a neutral evaluation prompt ("score objectively"). Every ad got 7.5-8.5. The evaluation was technically correct but useless for distinguishing quality tiers.

---

## Generation Strategy

### 2026-03-03 — 3 Variants Per Brief with Diverse Approaches

**Decision:** For each brief, generate 3 ad variants using different approaches (hooks, angles, emotional strategies) selected by VariantStrategy.

**Rationale:** A single generation attempt is a coin flip. Three diverse attempts dramatically increase the probability that at least one variant passes the quality gate. The approaches are intentionally different (e.g., empathy hook vs. statistic hook vs. social proof) to avoid generating three similar ads.

**Trade-off:** 3x the generation cost per brief. Worth it because generation (Gemini Flash) is cheap; the expensive step is evaluation (Gemini Pro).

### 2026-03-03 — Config-Driven Brief Interpreter (No LLM)

**Decision:** BriefInterpreter enriches briefs using YAML config (brand guidelines, audience triggers) without making an LLM call.

**Rationale:** Brief enrichment is deterministic — the same audience always gets the same emotional triggers and key messages. Using an LLM here would add cost and latency for zero benefit. The config-driven approach is also easier to debug and audit.

### 2026-03-04 — Gemini Flash for Generation, Pro for Evaluation

**Decision:** Use Gemini 2.5 Flash (cheap, fast) for ad generation and Gemini 2.5 Pro (expensive, accurate) for evaluation.

**Rationale:** Generation needs creativity and speed; evaluation needs precision and judgment. Flash is 16x cheaper per token than Pro. Since we generate 3 variants and evaluate each, the cost asymmetry matters. Pro's superior reasoning makes it a better judge.

---

## Iteration Effectiveness

### 2026-03-04 — Dimension-Level Weakness Diagnosis

**Decision:** When an ad fails, diagnose the weakest dimension specifically rather than asking the LLM to "make it better."

**Rationale:** Generic re-prompting ("improve this ad") produces unpredictable changes. Dimension-level diagnosis means the editor knows exactly what to fix (e.g., "emotional_resonance is 5.2 because the primary text uses only rational arguments") and what to preserve.

**Failed experiment:** Early iteration used a simple "rewrite to improve the score" prompt. This often improved the weak dimension but regressed others — a game of whack-a-mole. The preservation rules in the editing prompt ("DO NOT regress these dimensions") solved this.

### 2026-03-05 — 3-Strike Escalation: Continue → Escalate → Abandon

**Decision:** Maximum 3 edit attempts. On stalling (no improvement), escalate to fresh generation. After 3 total attempts, abandon.

**Rationale:** Editing has diminishing returns. If 2 surgical edits can't fix the ad, the fundamental approach is probably wrong. Escalation generates a completely new ad with a different angle, which often succeeds where editing failed.

**What we learned:** About 60-70% of failing ads are rescued by editing. The remaining ones are genuinely hard cases where the brief/approach combination doesn't produce quality output.

---

## Competitive Intelligence

### 2026-03-06 — Manual Competitor Ad Collection

**Decision:** Manually collect 20-30 competitor ads from Facebook Ad Library rather than scraping.

**Rationale:** Facebook's Ad Library has anti-scraping protections. Manual collection ensures we get real, currently-running ads from Princeton Review, Kaplan, Khan Academy, and Chegg. Quality of the corpus matters more than quantity.

**Trade-off:** Not scalable. A production system would need an automated collection pipeline. For this project, manual collection gives us a high-quality, curated corpus.

### 2026-03-06 — Pattern Taxonomy as Generation Context

**Decision:** Extract structural patterns (hook types, CTA styles, emotional triggers) from competitor ads and inject them into the generation prompt via BriefInterpreter.

**Rationale:** Rather than copying competitor ads, we extract what makes them work (or fail) and use those insights to inform our own generation. The taxonomy becomes a knowledge base of advertising strategies weighted by estimated effectiveness.

---

## Analytics & Self-Healing

### 2026-03-07 — Conservative Quality Ratchet

**Decision:** Auto-raise the quality threshold by 0.5 only when the last 3 cycles average > threshold + 1.0. Threshold never decreases.

**Rationale:** The ratchet prevents complacency — as the system proves it can consistently generate high-quality ads, the bar rises. The conservative trigger (3 sustained cycles, 1.0 margin) prevents premature ratcheting on a lucky run.

### 2026-03-07 — Self-Healing via Regression Detection

**Decision:** After each cycle, compare per-dimension averages to the previous cycle. If any dimension drops > 0.5 points, diagnose the regression using Gemini Pro and suggest a fix.

**Rationale:** Quality regressions happen silently. Without monitoring, a prompt change that improves one dimension could regress another. The self-healer provides a safety net and audit trail.

---

## What Failed

### Neutral Evaluation Prompts
As noted above, non-adversarial evaluation prompts produced scores clustered at 8-9 with no discrimination. Solved by explicit adversarial framing.

### Generic Iteration ("Make It Better")
Re-prompting without specific diagnosis produced unpredictable regressions. Solved by dimension-level weakness diagnosis + preservation rules.

### Over-Aggressive Ratcheting
An early ratchet config raised the threshold by 1.0 after 1 cycle. This caused a death spiral where nothing passed, triggering more iteration, burning cost, and still not passing. Solved by requiring 3 sustained cycles with a 0.5 raise.

### Single-Variant Generation
Generating 1 ad per brief had a ~40% pass rate. Generating 3 diverse variants raised effective pass rate to ~85%+ (at least one passes per brief). The cost increase was minimal because Flash generation is cheap.

---

## Scale & Polish

### 2026-03-10 — Error Resilience in Batch Processing

**Decision:** Wrap individual ad generation in try/except so a single LLM failure doesn't crash the batch.

**Rationale:** When generating 100+ ads, transient API errors (rate limits, timeouts, malformed responses) are inevitable. Error records are logged with `error_message` so failures are visible and auditable without stopping the pipeline.

### 2026-03-10 — Deterministic Seeding

**Decision:** Accept a `--seed` flag (default 42) and seed `random` at startup for reproducibility.

**Rationale:** Reproducible runs are essential for debugging and comparison. The same seed + same briefs should produce the same variant approach selections.

### 2026-03-10 — 35 Briefs for 100+ Ad Coverage

**Decision:** Expand from 12 to 35 briefs covering all 3 audience segments, both campaign goals, seasonal/urgency angles, social proof, and value/ROI messaging.

**Rationale:** 35 briefs × 3 variants = 105 ads per cycle, exceeding the 100+ target. The briefs cover diverse angles to stress-test the generation pipeline across the full messaging spectrum.
