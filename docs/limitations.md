# Limitations — Nerdy Ad Engine

An honest assessment of known limitations, their impact, and future directions.

---

## Evaluator Limitations

### LLM-as-Judge Bias
The evaluator uses Gemini Pro to score ads, which inherits LLM biases. Scores are internally consistent but not calibrated against real-world ad performance (CTR, conversion rate, ROAS). An ad scoring 8.5 in our system may or may not outperform a 7.0 ad in production.

**Impact:** Quality gate decisions are based on LLM judgment, not market data.
**Mitigation:** Calibration against reference ads with known performance tiers. Adversarial evaluation prompt reduces positive bias.
**Future:** Feed real CTR/conversion data back into evaluation to close the loop.

### No Real Performance Data
The system has no access to actual ad performance metrics. All quality assessments are based on LLM evaluation of ad copy structure, not measured user engagement.

**Impact:** Cannot validate whether "high-scoring" ads actually perform better in market.
**Future:** Integrate with Meta Ads API to track deployed ad performance and correlate with evaluation scores.

### Single-Evaluator Risk
Using one LLM (Gemini Pro) as the sole evaluator creates a single point of failure. If the model has blind spots, the entire quality signal is compromised.

**Future:** Multi-model evaluation panel (Gemini Pro + Claude + GPT-4) with score averaging for robustness.

---

## Generation Limitations

### Text-Only Output
The system generates ad copy only — no images, videos, or carousel formats. Real Facebook/Instagram ads are multi-modal, and copy effectiveness depends heavily on the creative pairing.

**Impact:** Generated ads are incomplete as production assets.
**Future:** Integrate with image generation APIs (DALL-E, Midjourney) for paired creative.

### Single Channel
All ads are formatted for Facebook/Instagram. No support for Google Ads, TikTok, LinkedIn, or other channels with different format constraints.

**Future:** Channel-aware format templates with platform-specific constraints.

### Single Product Focus
Currently optimized exclusively for Varsity Tutors SAT Test Prep. The brand guidelines, audience segments, and competitive intelligence are hardcoded to this domain.

**Impact:** Not generalizable without significant config changes.
**Future:** Multi-brand, multi-product config system with per-brand evaluator calibration.

### CTA Limited to 5 Options
The allowed CTA values ("Learn More", "Sign Up", "Get Started", "Book Now", "Try Free") are a subset of Facebook's options and hardcoded in the model validator.

**Impact:** Minor constraint. These 5 CTAs cover the primary use cases.

---

## Iteration Limitations

### Maximum 3 Edit Attempts
The escalation manager caps iteration at 3 attempts (continue → escalate → abandon). Some ads might benefit from additional editing passes.

**Impact:** ~15-30% of ads are abandoned after 3 attempts despite being potentially fixable.
**Trade-off:** More attempts = more cost with diminishing returns. 3 attempts captures the majority of rescuable ads.

### Editing Sometimes Regresses Other Dimensions
Despite preservation rules in the editing prompt, targeted edits occasionally regress previously-strong dimensions. The LLM doesn't always respect "don't change this part."

**Impact:** Some iteration cycles make the ad worse before making it better.
**Mitigation:** The iteration loop re-evaluates after each edit, so regressions are detected. Escalation to fresh generation provides a fallback.

### No Cross-Ad Learning
Each ad is iterated independently. The system doesn't learn from successful edits on one ad to inform editing on another within the same batch.

**Future:** Aggregate successful edit patterns and inject them as few-shot examples into the editing prompt.

---

## Competitive Intelligence Limitations

### Manual Collection
Competitor ads are manually collected from Facebook Ad Library, not automatically scraped. The corpus is a snapshot, not a live feed.

**Impact:** Competitive intelligence becomes stale over time. Manual collection doesn't scale.
**Future:** Automated ad collection pipeline with Facebook Ad Library API (if available) or approved scraping.

### Estimated Effectiveness
Pattern effectiveness is estimated by LLM analysis, not measured by actual ad performance data (impressions, clicks, conversions).

**Impact:** "High effectiveness" patterns are LLM opinions, not market-validated signals.
**Future:** Cross-reference with actual ad performance data where available.

### Small Corpus
20-30 competitor ads is a small sample. Pattern extraction may overfit to this specific set rather than capturing broad industry trends.

**Future:** Expand to 100+ competitor ads across more brands and time periods.

---

## Cost & Performance

### Pro Evaluation Is Most Expensive
Gemini Pro evaluation accounts for ~70% of total pipeline cost. Each ad requires at least 1 evaluation call, and failing ads require additional evaluation after each edit.

**Impact:** Cost scales linearly with ads generated. At 100+ ads per cycle, evaluation costs dominate.
**Future:** Use Flash for initial screening, Pro only for borderline cases. Cache evaluations for identical ad copy.

### No Caching
Every LLM call is made fresh. Identical prompts (e.g., evaluating the same ad copy twice) are not cached.

**Impact:** Wasted cost on duplicate evaluations.
**Future:** Content-addressable cache for evaluation results keyed on ad copy hash.

### Sequential Processing
Ads are processed sequentially within each brief. No concurrent API calls.

**Impact:** Slow at scale. 100 ads takes 15-30 minutes.
**Future:** Async/concurrent generation and evaluation with rate limiting.

---

## Analytics Limitations

### Quality Ratchet Is Conservative
The ratchet requires 3 sustained cycles above threshold + 1.0 before raising. This means slow adaptation to genuinely improved generation quality.

**Trade-off:** Intentional. Aggressive ratcheting caused a death spiral in early experiments.

### Self-Healer Suggestions Are Not Auto-Applied
The self-healer diagnoses regressions and suggests fixes, but does not automatically modify prompts or config. A human must review and apply the suggestions.

**Impact:** Self-healing is advisory, not autonomous.
**Future:** Auto-apply low-risk suggestions (e.g., adding examples to prompts) with rollback on regression.

---

## Infrastructure

### No Persistence Layer
All state is in JSON files and in-memory. No database, no API, no web dashboard.

**Future:** SQLite or PostgreSQL for ad storage, FastAPI for API, React dashboard for visualization.

### No Authentication or Multi-Tenancy
The system runs as a single-user CLI tool with no access control.

**Future:** Multi-tenant architecture with per-brand isolation and role-based access.

### No CI/CD Pipeline
Tests run locally via `make test`. No automated testing on push, no deployment pipeline.

**Future:** GitHub Actions for CI, automated deployment to cloud infrastructure.
