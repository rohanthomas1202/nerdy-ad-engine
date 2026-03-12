# Nerdy Ad Engine — Phased Implementation Plan

> **IMPORTANT RULES**:
> - **NEVER commit or push** code unless explicitly asked by the user
> - After each phase, a suggested commit message is provided — DO NOT execute it automatically
> - **Always use ports between 8020 and 8030** for any servers/services to avoid conflicts
> - **DO NOT move to the next phase** until the user explicitly asks

---

## Guiding Principles

- **Evaluator-first**: Phase 1 builds the evaluator before the generator exists
- **Zero failing tests gate**: `pytest` must be green before moving to the next phase
- **Each phase produces a runnable artifact** — never a half-built module
- **All LLM calls** route through `src/llm/client.py` with token/cost tracking from day one
- **Pydantic models** are the contract layer — modules communicate through typed structures, never raw dicts
- **Port range**: Any server, API, or service MUST use ports 8020-8030 only

---

## PHASE 1: Foundation — Project Skeleton, Config, Data Models, LLM Client, Basic Evaluator

**Status: [x] DONE** — 43 tests passing, 0 lint errors (2026-03-11)

### Dependencies
None. This is the starting point.

### Rationale
The evaluator is the single most important component (25% of scoring weight). Building it first — before a single ad is generated — lets you calibrate against reference ads and prove the system can distinguish quality.

### Files to Create

#### Project Root Scaffolding

1. **`pyproject.toml`**
   - Project metadata, pytest config, ruff config
   - Pin Python >=3.11
   - Dependencies: `google-generativeai`, `pydantic>=2.0`, `pyyaml`, `pytest`, `pytest-asyncio`, `ruff`, `matplotlib`, `pandas`
   - `[tool.pytest.ini_options]`: testpaths = ["tests"], pythonpath = [".", "src"]
   - `[tool.ruff]`: line-length = 100

2. **`requirements.txt`** — Flat pip-installable mirror of pyproject.toml deps

3. **`.env.example`** — Template: `GEMINI_API_KEY=your-key-here`

4. **`.gitignore`** — Standard Python + `.env`, `output/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`, `.ruff_cache/`

5. **`Makefile`** — Targets: `install`, `test`, `lint`, `run`, `demo` (placeholder)
   - Any `serve` or `run-server` target MUST use port 8020

6. **`README.md`** — Setup instructions, brief architecture overview, link to architecture.md

#### Config Files

7. **`config/settings.yaml`**
   - `models.generation`: gemini-2.0-flash, temperature 0.8, seed 42
   - `models.evaluation`: gemini-2.0-pro, temperature 0.1, seed 42
   - `models.editing`: same as evaluation
   - `thresholds.quality_gate`: 7.0
   - `thresholds.max_edit_attempts`: 3
   - `thresholds.variants_per_brief`: 3
   - `server.port`: 8020 (default port for any API/server)
   - `costs`: flash/pro input/output rates per 1k tokens
   - `weights`: clarity 0.20, value_proposition 0.25, call_to_action 0.20, brand_voice 0.15, emotional_resonance 0.20

8. **`config/brand_guidelines.yaml`**
   - Voice: empowering, knowledgeable, approachable, results-focused
   - Tone do's and don'ts
   - Product: Varsity Tutors by Nerdy, SAT test prep
   - Audiences: parents anxious about admissions, students stressed about scores, families comparing options
   - Competitors: Princeton Review, Kaplan, Khan Academy, Chegg

9. **`config/dimensions.yaml`**
   - 5 evaluation dimensions, each with: name, weight, description, measures, rubric_low/mid/high, calibration_examples (2 per dimension)

10. **`config/briefs.yaml`**
    - 10-15 ad briefs with: id, audience_segment, product, campaign_goal, tone_override, key_message

#### Data Files

11. **`data/reference_ads.json`** — 10-15 reference ads with: id, primary_text, headline, description, cta, performance_tier (high/medium/low), notes

12. **`data/competitor_ads.json`** — Empty array `[]` (populated in Phase 4)

13. **`data/patterns/taxonomy.json`** — Empty object `{}` (populated in Phase 4)

#### Source Files

14. **`src/__init__.py`** — Empty

15. **`src/models.py`** — All Pydantic data models:
    - `AdCopy`: primary_text (max 500), headline (max 40), description (max 125), cta (from allowed set)
    - `Brief`: id, audience_segment, product, campaign_goal, tone_override, key_message, enrichment_context
    - `DimensionScore`: dimension, score (1.0-10.0), rationale, confidence (0.0-1.0)
    - `EvaluationResult`: dimension_scores, aggregate_score, passed_quality_gate, weakest_dimension, evaluation_rationale
    - `AdRecord`: id, brief_id, variant_index, ad_copy, evaluation, iteration_history, status, costs, created_at, model_used
    - `Diagnosis`: weakest_dimension, score, problem_description, suggested_fix, preserve_dimensions
    - `LLMUsage`: model, input_tokens, output_tokens, cost_usd, call_type, duration_seconds
    - `CalibrationResult`: reference_ad_id, expected_tier, actual_scores, aggregate_score, alignment
    - `ExperimentEntry`: id, timestamp, hypothesis, change, result, metrics_before, metrics_after

16. **`src/llm/__init__.py`** — Empty

17. **`src/llm/client.py`** — `GeminiClient` class:
    - Loads API key from env, initializes flash + pro model instances
    - `generate(prompt, model_type, temperature, response_schema)` → (str, LLMUsage)
    - `generate_structured(prompt, response_type, model_type)` → (T, LLMUsage)
    - `total_cost` property, `usage_log` property, `reset_usage()` method
    - Rate limiting via `time.sleep(0.5)` between calls

18. **`src/llm/prompts.py`** — Prompt templates:
    - `EVALUATION_SYSTEM_PROMPT`: adversarial evaluator persona
    - `EVALUATION_SCORE_PROMPT`: takes ad_text, dimensions_rubric, calibration_examples
    - `CALIBRATION_PROMPT`: same structure for reference ad scoring
    - Placeholders for GENERATION_PROMPT, EDITING_PROMPT, DIAGNOSIS_PROMPT (Phase 2/3)

19. **`src/evaluate/__init__.py`** — Empty

20. **`src/evaluate/dimension_scorer.py`** — `DimensionScorer`:
    - Loads dimensions.yaml
    - `score(ad_copy)` → (list[DimensionScore], LLMUsage)

21. **`src/evaluate/aggregator.py`** — `Aggregator`:
    - Loads weights from settings.yaml
    - `aggregate(dimension_scores)` → EvaluationResult

22. **`src/evaluate/calibrator.py`** — `Calibrator`:
    - Loads reference_ads.json
    - `run_calibration()` → list[CalibrationResult]
    - `report(results)` → dict (alignment rate, avg score per tier, Spearman correlation)

23. **`src/evaluate/quality_gate.py`** — `QualityGate`:
    - `check(evaluation)` → "approved" | "needs_editing" | "failed"

#### Test Files

24. **`tests/__init__.py`** — Empty

25. **`tests/conftest.py`** — Shared fixtures: sample_ad_copy, sample_brief, sample_dimension_scores, mock_llm_client, settings_config

26. **`tests/test_models.py`** — 8-10 tests: model validation, field constraints, error on invalid data

27. **`tests/test_dimension_scorer.py`** — 4-5 tests: mock LLM, returns 5 scores, non-empty rationales, retry on bad JSON

28. **`tests/test_aggregator.py`** — 4-5 tests: weighted average, weakest dimension, boundary at 7.0

29. **`tests/test_quality_gate.py`** — 3-4 tests: approved/needs_editing routing, configurable threshold

30. **`tests/test_calibrator.py`** — 3-4 tests: mock scorer, alignment detection, report computation

31. **`tests/test_llm_client.py`** — 5-6 tests: mock google.generativeai, usage logging, cost accumulation, reset, structured parsing

### Tests to Run
```bash
make install
make test    # Target: 28-35 tests, 0 failures
make lint    # Zero ruff violations
```

### Manual Testing Steps
1. Run `make install` — verify clean install
2. Run `make test` — all tests pass
3. Run `make lint` — no violations
4. Set `GEMINI_API_KEY` in `.env`
5. Run `python -m src.evaluate.calibrator` — scores all reference ads, prints calibration report
6. **Verify**: Do high-tier reference ads score > 7.0? Do low-tier score < 5.0?
7. If evaluator can't distinguish quality: iterate on prompts/rubrics in dimensions.yaml until alignment >= 80%. **DO NOT proceed to Phase 2 until this works.**
8. Check `client.total_cost` after calibration — verify token tracking matches expected counts

### Success Criteria
- [ ] All Pydantic models validate correctly and reject invalid data
- [ ] LLM client tracks tokens and costs accurately (mock tests)
- [ ] DimensionScorer returns structured 5-dimension evaluations
- [ ] Aggregator produces correct weighted averages
- [ ] QualityGate routes correctly at 7.0 boundary
- [ ] Calibrator ranks high-tier ads above low-tier with >= 80% alignment
- [ ] `make test` passes with 28+ tests, zero failures
- [ ] `make lint` passes

### Suggested Commit Message (DO NOT COMMIT — wait for user to ask)
```
feat: Phase 1 — Foundation with evaluator-centric architecture

Add project scaffolding, Pydantic data models, unified Gemini LLM client
with token/cost tracking, 5-dimension evaluator with calibration against
reference ads, quality gate, and comprehensive test suite (28+ tests).

Key components:
- config/ — settings, brand guidelines, dimensions, briefs
- src/models.py — typed contract layer for all modules
- src/llm/ — unified Gemini client (Flash + Pro) with cost tracking
- src/evaluate/ — dimension scorer, aggregator, calibrator, quality gate
- tests/ — full mock-based test coverage
```

---

## PHASE 2: Generation Loop — Brief Interpreter, Writer, Variant Strategy, Basic Pipeline

**Status: [x] DONE** — 62 tests passing, 0 lint errors (2026-03-11)

### Dependencies
Phase 1: models.py, llm/client.py, evaluate/* (all 4 modules), config files

### Rationale
With a calibrated evaluator, you can now generate ads and immediately know whether they're good. The generation module is the "easy" part — the evaluator provides reliable signal.

### Files to Create

1. **`src/generate/__init__.py`** — Empty

2. **`src/generate/brief_interpreter.py`** — `BriefInterpreter`:
   - Loads brand_guidelines.yaml and briefs.yaml
   - `interpret(brief)` → Brief (enriched with brand voice, audience triggers, product features)
   - `load_briefs()` → list[Brief]
   - Deterministic string assembly — NO LLM call (zero cost, auditable)

3. **`src/generate/writer.py`** — `Writer`:
   - `write(enriched_brief, variant_approach)` → (AdCopy, LLMUsage)
   - Uses Gemini Flash with GENERATION_PROMPT template
   - Returns structured JSON parsed into AdCopy

4. **`src/generate/variant_strategy.py`** — `VariantStrategy`:
   - `APPROACHES`: list of hook_type + angle + instruction combos
   - `select_approaches(brief, count=3)` → list[str] (maximally diverse)
   - No LLM call — pure strategy logic

### Files to Modify

5. **`src/llm/prompts.py`** — Fill in:
   - `GENERATION_SYSTEM_PROMPT`: expert ad copywriter persona
   - `GENERATION_PROMPT`: takes enriched_context, variant_instruction, format_constraints

6. **`src/main.py`** — `Pipeline` class:
   - `run_single_brief(brief)` → list[AdRecord]: interpret → 3 variants → generate → evaluate → route
   - `run_batch(briefs)` → list[AdRecord]: process all briefs, save results
   - `save_results(records)`: to output/ad_library.json and output/failed_ads.json
   - `if __name__ == "__main__"`: load config, run batch, print summary

### Test Files

7. **`tests/test_brief_interpreter.py`** — 4 tests: enrichment adds context, load_briefs parses yaml, brand voice included, audience-specific content

8. **`tests/test_writer.py`** — 4 tests: mock LLM returns valid AdCopy, character limits, prompt includes variant instruction, usage tracked

9. **`tests/test_variant_strategy.py`** — 4 tests: returns exactly count approaches, different hook types, audience-appropriate angles, >= 6 approaches available

10. **`tests/test_pipeline.py`** — 4 tests: mock LLM, run_single_brief produces 3 AdRecords, evaluations attached, status set correctly, save produces valid JSON

### Tests to Run
```bash
make test    # Target: 44-50 tests, 0 failures
make lint    # Zero violations
```

### Manual Testing Steps
1. `make test` — all Phase 1 + 2 tests pass
2. Run `python -m src.main` with real API key, 2-3 briefs (6-9 ads)
3. Inspect `output/ad_library.json`:
   - Read the ads. Do they sound like Varsity Tutors?
   - Are 3 variants per brief genuinely different hooks?
   - Do scores feel right? Compare to your judgment
   - Any false positives (bad ads scoring > 7)? Evaluator too lenient
   - Any false negatives (good ads scoring < 7)? Evaluator too harsh
4. Check total cost printed. For 9 ads, expect ~$0.05-0.15
5. Document observations in decision log

### Success Criteria
- [ ] BriefInterpreter produces enriched briefs with audience-appropriate context
- [ ] Writer generates structurally valid AdCopy (character limits, valid CTA)
- [ ] VariantStrategy produces diverse approaches (no duplicate hooks within a brief)
- [ ] Pipeline orchestrates full generate-evaluate flow for multiple briefs
- [ ] Output JSON files contain valid, scored AdRecords
- [ ] At least some ads pass 7.0 quality gate on first generation
- [ ] `make test` passes with 44+ tests, zero failures

### Suggested Commit Message (DO NOT COMMIT — wait for user to ask)
```
feat: Phase 2 — Generation loop with multi-variant strategy

Add brief interpreter (config-driven enrichment), ad copy writer
(Gemini Flash), variant strategy (diverse hooks/angles), and pipeline
orchestrator. Full generate → evaluate → route flow for multiple briefs.

Key components:
- src/generate/ — brief interpreter, writer, variant strategy
- src/main.py — Pipeline orchestrator with batch processing
- output/ — ad_library.json and failed_ads.json
- 16 new tests (44+ total)
```

---

## PHASE 3: Feedback Loop — Weakness Diagnosis, Targeted Editing, Escalation

**Status: [x] DONE** — 80 tests passing, 0 lint errors (2026-03-11)

### Dependencies
Phase 2: src/main.py (Pipeline), src/generate/*, src/evaluate/*

### Rationale
This transitions from "generate and hope" to "generate, diagnose, fix, verify." Dimension-level diagnosis and surgical repair is THE core differentiator vs naive retry. The spec explicitly says "re-prompting is not iteration."

### Files to Create

1. **`src/iterate/__init__.py`** — Empty

2. **`src/iterate/weakness_diagnostician.py`** — `WeaknessDiagnostician`:
   - `diagnose(ad_copy, evaluation)` → (Diagnosis, LLMUsage)
   - Uses Gemini Pro with DIAGNOSIS_PROMPT
   - Must produce SPECIFIC guidance: not "make it more emotional" but "the primary text uses only rational arguments — add a parent-perspective opening that taps into college admission anxiety"

3. **`src/iterate/targeted_editor.py`** — `TargetedEditor`:
   - `edit(ad_copy, diagnosis)` → (AdCopy, LLMUsage)
   - Uses Gemini Pro (not Flash — editing requires nuance)
   - Surgical: "Rewrite ONLY the parts addressing [weak dimension]. Keep headline and CTA unchanged."

4. **`src/iterate/escalation.py`** — `EscalationManager`:
   - `should_continue(attempt, current_score, previous_score)` → "continue" | "escalate" | "abandon"
   - `escalate(brief, diagnosis)` → modified variant instruction for fresh generation

### Files to Modify

5. **`src/main.py`** — Extend Pipeline:
   - New `iterate_ad(ad_record)` → AdRecord: diagnose → edit → re-evaluate → check gate → check escalation
   - Modify `run_single_brief()`: after generation, iterate on failing ads
   - Add logging: "Ad X: attempt 2/3, score improved 5.8 -> 6.4"

6. **`src/llm/prompts.py`** — Add:
   - `DIAGNOSIS_PROMPT`: ad_text, dimension_scores, weakest_dimension
   - `EDITING_PROMPT`: ad_text, diagnosis, preserve_instructions
   - `ESCALATION_GENERATION_PROMPT`: brief, failed_diagnosis

### Test Files

7. **`tests/test_weakness_diagnostician.py`** — 4 tests: mock LLM, correct weakest dimension, specific diagnosis, preserve_dimensions lists strong ones

8. **`tests/test_targeted_editor.py`** — 5 tests: mock LLM, valid AdCopy, diagnosis in prompt, preservation instructions, uses Pro model

9. **`tests/test_escalation.py`** — 4 tests: continue on improvement, abandon at max, escalate on regression, escalation references diagnosis

10. **`tests/test_iteration_integration.py`** — 4 tests: mock ad scoring 5.5 then 7.2 after edit, approved after 1 edit, iteration_history has 2 entries, failed after 3 attempts, cost tracking includes iterations

### Tests to Run
```bash
make test    # Target: 61-70 tests, 0 failures
make lint    # Zero violations
```

### Manual Testing Steps
1. `make test` — all Phase 1-3 tests pass
2. Run `python -m src.main` with 3-5 briefs. Observe:
   - How many ads pass first generation vs after editing?
   - Are diagnoses specific and actionable?
   - Do edited ads improve on the diagnosed weakness?
   - Does weakest dimension score go UP without others dropping?
   - Any ads enter escalation path?
3. Manually trace ONE ad's full lifecycle: generation → evaluation → diagnosis → edit → re-evaluation
4. Document iteration effectiveness: "Out of 15 ads, 8 passed first try. 5 rescued by editing (avg 1.5 edits). 2 failed. Editor improved emotional_resonance most (+1.8 avg)."

### Success Criteria
- [ ] Diagnostician produces specific, actionable diagnoses
- [ ] Editor produces ads that score higher on diagnosed weak dimension
- [ ] Strong dimensions preserved (no > 0.5 point regression on non-target dimensions)
- [ ] Escalation logic routes correctly
- [ ] Pass rate >= 70% of all ads ultimately approved
- [ ] `make test` passes with 61+ tests, zero failures

### Suggested Commit Message (DO NOT COMMIT — wait for user to ask)
```
feat: Phase 3 — Feedback loop with targeted editing and escalation

Add weakness diagnostician (dimension-level diagnosis), targeted editor
(surgical rewrites preserving strong dimensions), and escalation logic
(3-strike with fresh generation fallback). Integrate iteration loop
into pipeline orchestrator.

Key components:
- src/iterate/ — diagnostician, editor, escalation
- src/main.py — iterate_ad() inner feedback loop
- 17 new tests (61+ total)
```

---

## PHASE 4: Competitive Intelligence — Meta Ad Library Analysis, Pattern Extraction

**Status: [ ] NOT STARTED**

### Dependencies
Phase 2: brief_interpreter (pattern injection), variant_strategy (pattern-informed approaches)
Phase 3: full pipeline working to measure improvement from competitive patterns

### Rationale
+10 bonus points. Manual collection of 20-30 competitor ads + LLM analysis to extract structural patterns (hooks, CTAs, angles). Patterns injected into generation prompts.

### Files to Create

1. **`src/research/__init__.py`** — Empty

2. **`src/research/competitor_analyzer.py`** — `CompetitorAnalyzer`:
   - `analyze_ad(ad)` → (dict, LLMUsage): extracts hook_type, angle, cta_style, emotional_triggers, structural_template, estimated_effectiveness
   - `analyze_batch()` → (list[dict], LLMUsage)
   - `extract_top_patterns(analyses, top_n=10)` → list[dict]: frequency counts + effectiveness ranking

3. **`src/research/reference_analyzer.py`** — `ReferenceAnalyzer`:
   - `analyze_performance_correlations()` → (dict, LLMUsage): patterns in high-tier vs low-tier ads

4. **`src/research/pattern_taxonomy.py`** — `PatternTaxonomy`:
   - `build(competitor_patterns, reference_patterns)` → dict
   - `save(taxonomy)` / `load()` → data/patterns/taxonomy.json
   - Schema: `{"hooks": [...], "ctas": [...], "angles": [...], "structures": [...]}`

### Files to Modify

5. **`src/generate/brief_interpreter.py`** — `interpret()` now loads taxonomy.json and appends patterns to enrichment_context (backward-compatible: works without taxonomy)

6. **`src/generate/variant_strategy.py`** — New `select_from_taxonomy(taxonomy, brief, count=3)`: bias toward high-effectiveness patterns

7. **`src/main.py`** — Add `run_research()` method, `--research` flag

8. **`src/llm/prompts.py`** — Add `COMPETITOR_ANALYSIS_PROMPT`, `REFERENCE_ANALYSIS_PROMPT`

### Data to Populate

9. **`data/competitor_ads.json`** — 20-30 real competitor ads from Meta Ad Library (Princeton Review, Kaplan, Khan Academy, Chegg)

### Test Files

10. **`tests/test_competitor_analyzer.py`** — 4 tests: mock LLM, all fields returned, frequency counts correct, empty list handled

11. **`tests/test_reference_analyzer.py`** — 3 tests: mock LLM, tier separation, patterns include hooks/angles/structures

12. **`tests/test_pattern_taxonomy.py`** — 4 tests: build merges patterns, save/load roundtrip, expected structure, empty inputs

13. **`tests/test_enriched_generation.py`** — 3 tests: enrichment includes taxonomy, variant strategy prefers high-effectiveness, backward compatible without taxonomy

### Tests to Run
```bash
make test    # Target: 75-84 tests, 0 failures
make lint    # Zero violations
```

### Manual Testing Steps
1. `make test` — all Phase 1-4 tests pass
2. Populate `data/competitor_ads.json` with real ads
3. Run `python -m src.main --research`
4. Inspect `data/patterns/taxonomy.json`:
   - Are extracted patterns meaningful?
   - Are hook types diverse?
   - Do effectiveness ratings make sense?
5. Run full pipeline with 5 briefs. Compare results to Phase 3 (without competitive intel):
   - Did average quality scores improve?
   - Are generated ads noticeably different?
   - Are variant approaches more diverse?
6. Document: "Competitive intelligence extracted N patterns. Top hooks: [list]. Injecting patterns improved avg score from X to Y."

### Success Criteria
- [ ] CompetitorAnalyzer extracts structured patterns from competitor ads
- [ ] ReferenceAnalyzer identifies high-performance correlations
- [ ] PatternTaxonomy produces valid, structured taxonomy
- [ ] BriefInterpreter incorporates taxonomy patterns
- [ ] VariantStrategy selects taxonomy-informed approaches
- [ ] Measurable improvement: +0.3 avg score after injecting competitive intel
- [ ] `make test` passes with 75+ tests, zero failures

### Suggested Commit Message (DO NOT COMMIT — wait for user to ask)
```
feat: Phase 4 — Competitive intelligence with pattern extraction

Add research module: competitor ad analyzer (Meta Ad Library patterns),
reference ad analyzer (performance correlations), and pattern taxonomy
builder. Inject extracted patterns into generation pipeline for
measurably improved ad quality. (+10 bonus points)

Key components:
- src/research/ — competitor analyzer, reference analyzer, taxonomy
- data/competitor_ads.json — 20-30 real competitor ads
- data/patterns/taxonomy.json — extracted hook/CTA/angle patterns
- 14 new tests (75+ total)
```

---

## PHASE 5: Analytics & Self-Healing — Quality Tracker, Token Tracker, Ratchet, Self-Healer

**Status: [ ] NOT STARTED**

### Dependencies
Phase 3: full iteration pipeline producing AdRecords with iteration_history
Phase 4: taxonomy data for pattern effectiveness context

### Rationale
Speed of Optimization (15% weight) requires performance-per-token economics and self-healing. This phase adds meta-intelligence: the system monitors itself, detects regressions, auto-adjusts, and tracks ROI.

### Files to Create

1. **`src/analytics/__init__.py`** — Empty

2. **`src/analytics/quality_tracker.py`** — `QualityTracker`:
   - `track(records)` → dict: per-dimension averages, per-cycle trends, pass rates
   - `plot_trends(trends, output_path)` → quality_trends.png (matplotlib)
   - `detect_regressions(trends)` → list of dimension drops > 0.5 points

3. **`src/analytics/token_tracker.py`** — `TokenTracker`:
   - `summarize()` → dict: total_cost, cost_per_ad, cost_per_approved_ad, cost_by_call_type, cost_by_model, quality_per_dollar
   - `plot_cost_dashboard(summary, output_path)` → cost_dashboard.png

4. **`src/analytics/quality_ratchet.py`** — `QualityRatchet`:
   - `check_ratchet(trends)` → (new_threshold, did_ratchet)
   - Raise by 0.5 only when last 3 cycles avg > threshold + 1.0
   - Threshold NEVER decreases

5. **`src/analytics/self_healer.py`** — `SelfHealer`:
   - `diagnose_regression(regression, recent_records)` → (str, LLMUsage)
   - `suggest_fix(diagnosis)` → str
   - `heal(regressions, recent_records)` → list of {dimension, diagnosis, fix}

6. **`src/analytics/experiment_logger.py`** — `ExperimentLogger`:
   - `log_experiment(entry)` / `get_experiments()` / `summary()`
   - Persists to output/experiment_log.json

### Files to Modify

7. **`src/models.py`** — Add `cycle: int = 0` to AdRecord

8. **`src/main.py`** — After each batch cycle:
   - Call quality_tracker, token_tracker, quality_ratchet
   - If regressions: call self_healer
   - Log experiment
   - Add `--cycles N` CLI arg for multi-cycle runs
   - Generate charts after all cycles

9. **`src/llm/prompts.py`** — Add `SELF_HEAL_DIAGNOSIS_PROMPT`

### Test Files

10. **`tests/test_quality_tracker.py`** — 4 tests: trend computation, regression detection (0.6 flagged, 0.4 not), per-dimension breakdown, single cycle

11. **`tests/test_token_tracker.py`** — 4 tests: cost aggregation, cost_per_ad, quality_per_dollar, empty log

12. **`tests/test_quality_ratchet.py`** — 4 tests: triggers after 3 cycles above, no trigger at 2, never decreases, raises by exactly 0.5

13. **`tests/test_self_healer.py`** — 3 tests: mock LLM diagnosis, non-empty result, actionable suggestion

14. **`tests/test_experiment_logger.py`** — 3 tests: log adds entry, save/load roundtrip, summary readable

### Tests to Run
```bash
make test    # Target: 93-102 tests, 0 failures
make lint    # Zero violations
```

### Manual Testing Steps
1. `make test` — all Phase 1-5 tests pass
2. Run `python -m src.main --cycles 5` with 5 briefs per cycle (75 total ads)
3. Inspect:
   - `output/quality_trends.png` — upward trends across cycles?
   - `output/cost_dashboard.png` — cost breakdown, quality_per_dollar improving?
   - `output/experiment_log.json` — meaningful data?
4. Artificially degrade generation prompt for one cycle — verify self_healer detects and diagnoses regression
5. If avg scores consistently > 8.0, verify ratchet raises threshold to 7.5
6. Document: total cost for 75 ads, quality_per_dollar, self-healing effectiveness, ratchet behavior

### Success Criteria
- [ ] QualityTracker produces accurate per-dimension trend data
- [ ] TokenTracker computes correct cost metrics including quality_per_dollar
- [ ] QualityRatchet raises threshold only when warranted (conservative, monotonic)
- [ ] SelfHealer detects regressions and produces specific diagnoses
- [ ] ExperimentLogger persists structured history
- [ ] Charts generated and visually meaningful
- [ ] `make test` passes with 93+ tests, zero failures

### Suggested Commit Message (DO NOT COMMIT — wait for user to ask)
```
feat: Phase 5 — Analytics engine with self-healing quality monitor

Add quality tracker (per-dimension trends + charts), token tracker
(performance-per-token economics), quality ratchet (auto-raise threshold),
self-healer (detect + diagnose regressions), and experiment logger.
Multi-cycle pipeline support with --cycles flag.

Key components:
- src/analytics/ — tracker, token tracker, ratchet, self-healer, logger
- output/ — quality_trends.png, cost_dashboard.png, experiment_log.json
- 18 new tests (93+ total)
```

---

## PHASE 6: Scale & Polish — 100+ Ads, Dashboards, Decision Log, Demo Mode

**Status: [ ] NOT STARTED**

### Dependencies
All of Phases 1-5. Integration, scale testing, documentation, presentation.

### Rationale
Spec requires 50+ ads (target 100-150+), complete decision log, evaluation report, quality metrics, and demo. This phase runs at scale, fixes edge cases, and produces all deliverables.

### Files to Create

1. **`docs/decision_log.md`** — The interview document:
   - Timestamped entries for each major decision
   - Sections: Architecture, Evaluator Calibration, Generation Strategy, Iteration Effectiveness, Competitive Intel, Analytics, What Failed, Limitations
   - Must include failed experiments and honest limitations

2. **`docs/limitations.md`** — Honest assessment:
   - Evaluator: LLM-as-judge bias, no real CTR data
   - Generation: no images, single channel
   - Iteration: max 3 attempts, editing sometimes regresses
   - Competitive intel: manual collection, no live scraping
   - Cost: Pro evaluation most expensive step
   - Future: A/B testing, multi-modal, live Meta integration

3. **`src/demo.py`** — Demo mode (3-5 min walkthrough):
   - Calibration demo → single brief pipeline → quality trends → cost dashboard → top 3 ads
   - If serving a dashboard, use port 8020 (configurable via settings.yaml `server.port`)

### Files to Modify

4. **`src/main.py`** — Production hardening:
   - `--count N` (default 100), `--demo`, `--output-dir`
   - `--port` flag defaults to 8020 (range 8020-8030 only)
   - Error handling: single ad failure doesn't crash batch
   - Progress: "Brief 5/15, variant 2/3, cycle 3/5... [47/100 ads, 34 approved]"
   - Deterministic seeding for reproducibility

5. **`src/models.py`** — Add `error_message: str | None = None` for failed ads

6. **`config/briefs.yaml`** — Expand to 30-35 briefs (× 3 variants = 100+ ads)

### Test Files

7. **`tests/test_pipeline_integration.py`** — 5-6 tests: full e2e flow, batch (3 briefs × 3 variants = 9 ads), error resilience (inject LLM failure), output files generated, deterministic with seed

8. **`tests/test_demo.py`** — 2 tests: runs without crash (mock LLM), expected output sections

### Tests to Run
```bash
make test    # Target: 100-112 tests, 0 failures
make lint    # Zero violations
```

### Manual Testing Steps
1. `make test` — all tests pass (100+ tests, zero failures)
2. Full production run: `python -m src.main --count 120 --cycles 7`
   - Runtime: 15-30 minutes
   - Cost: ~$1-3
3. Inspect outputs:
   - `output/ad_library.json` — 80+ approved ads (75%+ approval rate)
   - `output/failed_ads.json` — 20-40 failed with full iteration history
   - `output/quality_trends.png` — clear upward trend over 7 cycles
   - `output/cost_dashboard.png` — cost breakdown with quality_per_dollar
   - `output/experiment_log.json` — 7+ experiments
   - `output/calibration_report.json` — evaluator alignment
4. Read 10 random approved ads — genuinely good? Would you run on Facebook?
5. Read 5 random failed ads — genuinely bad? Evaluator rationale sensible?
6. Run demo: `python -m src.main --demo` — completes in < 2 min, compelling story
7. `make lint` — zero violations
8. Review `docs/decision_log.md` — reads like senior engineer's honest account? Includes failures?
9. Review `docs/limitations.md` — honest and specific?

### Success Criteria
- [ ] 100+ ads generated with full dimension scores and rationales
- [ ] Quality improvement across 3+ cycles (measurable in charts)
- [ ] Approval rate >= 70%
- [ ] Total cost < $5 for 100+ ads
- [ ] quality_per_dollar computed and reported
- [ ] All output artifacts generated
- [ ] Decision log complete, honest, timestamped
- [ ] Limitations doc specific and actionable
- [ ] Demo runs end-to-end and is presentable
- [ ] `make test` passes with 100+ tests, zero failures
- [ ] `make lint` zero violations
- [ ] Error handling: no crashes on LLM failures
- [ ] Deterministic with seeds
- [ ] Any servers use ports 8020-8030 only

### Suggested Commit Message (DO NOT COMMIT — wait for user to ask)
```
feat: Phase 6 — Scale to 100+ ads with demo mode and documentation

Production hardening with error resilience, progress reporting, and
deterministic seeding. Expand briefs to 30+, generate 100+ ads across
7 cycles. Add demo mode, decision log, and limitations doc.

Key deliverables:
- 100+ scored ads in output/ad_library.json
- Quality trend and cost dashboard visualizations
- docs/decision_log.md — honest engineering narrative
- docs/limitations.md — transparent assessment
- Demo mode for 3-5 minute walkthrough
- 105+ tests, zero failures
```

---

## KEY RISK: Evaluator Calibration

The entire system hinges on the evaluator being reliable. If Phase 1 calibration shows the evaluator cannot distinguish high-tier from low-tier reference ads:

**STOP. Do not proceed to Phase 2.**

Instead, iterate on:
1. The evaluation prompt in `src/llm/prompts.py`
2. The rubrics in `config/dimensions.yaml`
3. The calibration examples

Until alignment reaches 80%+. This might take several hours of prompt engineering. Document every iteration in the decision log — this IS the kind of genuine engineering thinking reviewers want to see.

---

## Summary Table

| Phase | Focus | Files | Tests | Cum. Tests | Status |
|-------|-------|-------|-------|------------|--------|
| 1 | Foundation + Evaluator | 24 new | 43 | 43 | [x] DONE |
| 2 | Generation Loop | 6 new, 2 modified | 19 | 62 | [x] DONE |
| 3 | Feedback Loop | 4 new, 2 modified | 18 | 80 | [x] DONE |
| 4 | Competitive Intel | 4 new, 4 modified | ~14 | ~79 | [ ] |
| 5 | Analytics + Self-Heal | 6 new, 3 modified | ~18 | ~97 | [ ] |
| 6 | Scale + Polish | 3 new, 3 modified | ~8 | ~105 | [ ] |
