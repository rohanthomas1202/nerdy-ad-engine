# Nerdy Ad Engine — Repository Structure & System Architecture

---

## GitHub Repository Structure

```
nerdy-ad-engine/
│
├── README.md                          # Project overview, setup, usage, results summary
├── initial_plan.md                    # Strategic plan
├── architecture.md                    # This file — repo structure + system architecture
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project metadata + tool config (pytest, ruff)
├── .env.example                       # Template for API keys (GEMINI_API_KEY)
├── .gitignore                         # Standard Python + .env + output artifacts
├── Makefile                           # One-command shortcuts: make run, make test, make demo
│
├── config/
│   ├── settings.yaml                  # Global config: models, thresholds, costs, weights
│   ├── brand_guidelines.yaml          # Varsity Tutors brand voice, tone, constraints
│   ├── briefs.yaml                    # Ad briefs (audience, product, goal, campaign type)
│   └── dimensions.yaml                # 5 evaluation dimensions with rubrics + calibration anchors
│
├── data/
│   ├── reference_ads.json             # Varsity Tutors reference ads with known performance
│   ├── competitor_ads.json            # Scraped/collected competitor ads (Meta Ad Library)
│   └── patterns/
│       └── taxonomy.json              # Extracted hook/CTA/angle patterns from research
│
├── src/
│   ├── __init__.py
│   ├── main.py                        # ORCHESTRATOR — entry point, pipeline control
│   ├── models.py                      # Pydantic data models (Ad, Score, Brief, Diagnosis, etc.)
│   │
│   ├── research/
│   │   ├── __init__.py
│   │   ├── competitor_analyzer.py     # Analyze competitor ads → extract patterns
│   │   ├── reference_analyzer.py      # Analyze reference ads → performance correlations
│   │   └── pattern_taxonomy.py        # Build structured pattern taxonomy
│   │
│   ├── generate/
│   │   ├── __init__.py
│   │   ├── brief_interpreter.py       # Enrich brief with guidelines + patterns
│   │   ├── writer.py                  # LLM ad copy generation (Gemini Flash)
│   │   └── variant_strategy.py        # Multi-variant approach selection (3 per brief)
│   │
│   ├── evaluate/
│   │   ├── __init__.py
│   │   ├── dimension_scorer.py        # Score each of 5 dimensions independently
│   │   ├── calibrator.py              # Validate evaluator against reference ads
│   │   ├── aggregator.py              # Weighted aggregate + confidence
│   │   └── quality_gate.py            # 7.0+ threshold routing
│   │
│   ├── iterate/
│   │   ├── __init__.py
│   │   ├── weakness_diagnostician.py  # Identify weakest dimension + specific diagnosis
│   │   ├── targeted_editor.py         # Surgical rewrite of weak parts (Gemini Pro)
│   │   └── escalation.py             # 3-strike escalation logic
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── quality_tracker.py         # Per-cycle dimension trends + charts
│   │   ├── token_tracker.py           # Cost per ad, quality per dollar
│   │   ├── quality_ratchet.py         # Auto-raise minimum threshold
│   │   ├── self_healer.py            # Detect + auto-fix quality regressions
│   │   └── experiment_logger.py       # Structured experiment log (hypothesis → result)
│   │
│   └── llm/
│       ├── __init__.py
│       ├── client.py                  # Unified Gemini API client (Flash + Pro)
│       └── prompts.py                 # All prompt templates (separated from logic)
│
├── output/
│   ├── ad_library.json                # All approved ads with scores + metadata
│   ├── failed_ads.json                # Ads that failed after max edits (for analysis)
│   ├── calibration_report.json        # Evaluator calibration results
│   ├── quality_trends.png             # Dimension-level quality over cycles
│   ├── cost_dashboard.png             # Performance-per-token visualization
│   └── experiment_log.json            # Full experiment history
│
├── docs/
│   ├── decision_log.md                # THE INTERVIEW — timestamped, honest, personal
│   └── limitations.md                 # Known limitations + future improvements
│
└── tests/
    ├── __init__.py
    ├── test_dimension_scorer.py       # Evaluator produces valid structured scores
    ├── test_calibrator.py             # Calibration correctly ranks reference ads
    ├── test_quality_gate.py           # Threshold routing works correctly
    ├── test_writer.py                 # Generator produces valid ad structure
    ├── test_weakness_diagnostician.py # Diagnosis identifies correct weakest dimension
    ├── test_targeted_editor.py        # Editor preserves strong dimensions
    ├── test_token_tracker.py          # Cost tracking accumulates correctly
    ├── test_quality_ratchet.py        # Threshold only increases, never decreases
    ├── test_self_healer.py            # Quality drops detected and flagged
    └── test_pipeline_integration.py   # End-to-end: brief → approved ad
```

---

## System Architecture Diagram

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           AUTONOMOUS CONTENT GENERATION SYSTEM              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌────────────────────────────────────────────────────────────────────────┐  ║
║  │                        ORCHESTRATOR (main.py)                          │  ║
║  │                                                                        │  ║
║  │  • Pipeline state machine (RESEARCH → GENERATE → EVALUATE → ITERATE)  │  ║
║  │  • Cycle management (7+ iteration cycles)                              │  ║
║  │  • Batch scheduling (briefs × variants)                                │  ║
║  │  • Global config loading (settings.yaml)                               │  ║
║  └───────┬──────────────┬──────────────┬──────────────┬──────────────────┘  ║
║          │              │              │              │                      ║
║     ┌────▼────┐    ┌────▼────┐    ┌────▼────┐   ┌────▼─────┐               ║
║     │RESEARCH │    │GENERATE │    │EVALUATE │   │ ITERATE  │               ║
║     └────┬────┘    └────┬────┘    └────┬────┘   └────┬─────┘               ║
║          │              │              │              │                      ║
║  ════════╪══════════════╪══════════════╪══════════════╪══════════════════   ║
║          │              │              │              │                      ║
║          ▼              ▼              ▼              ▼                      ║
║                                                                              ║
║  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  ║
║  │  LLM CLIENT     │  │  DATA MODELS    │  │  ANALYTICS ENGINE           │  ║
║  │  (llm/)         │  │  (models.py)    │  │  (analytics/)               │  ║
║  │                 │  │                 │  │                             │  ║
║  │  Gemini Flash ──┼──┤  Ad             │  │  quality_tracker ──┐       │  ║
║  │  (generation)   │  │  Brief          │  │  token_tracker ───┤       │  ║
║  │                 │  │  Score          │  │  quality_ratchet ──┤→ PNG  │  ║
║  │  Gemini Pro ────┼──┤  Diagnosis      │  │  self_healer ─────┤  JSON │  ║
║  │  (eval + edit)  │  │  Experiment     │  │  experiment_log ──┘       │  ║
║  │                 │  │  CalibResult    │  │                             │  ║
║  │  Token counting │  │                 │  │  Feeds → decision_log.md   │  ║
║  │  Cost tracking  │  │  (Pydantic)     │  │  Feeds → output/*.png      │  ║
║  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                              DATA FLOW                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  config/briefs.yaml ──┐                                                      ║
║  config/brand.yaml ───┤                                                      ║
║  data/patterns/ ──────┤                                                      ║
║                       ▼                                                      ║
║              ┌─────────────────┐     ┌──────────────────┐                    ║
║              │  BRIEF          │     │  RESEARCH        │                    ║
║              │  INTERPRETER    │◄────│  competitor_ads   │                    ║
║              │                 │     │  reference_ads    │                    ║
║              │  Enriches brief │     │  → patterns.json  │                    ║
║              │  with patterns  │     └──────────────────┘                    ║
║              └────────┬────────┘                                             ║
║                       │ enriched brief                                       ║
║                       ▼                                                      ║
║              ┌─────────────────┐                                             ║
║              │  WRITER         │                                             ║
║              │  (Gemini Flash) │──── 3 variants per brief                    ║
║              └────────┬────────┘     (question/stat/story hooks)             ║
║                       │                                                      ║
║                       ▼                                                      ║
║              ┌─────────────────┐                                             ║
║              │  EVALUATOR      │                                             ║
║              │  (Gemini Pro)   │──── 5 dimension scores + rationale          ║
║              │                 │     + confidence per dimension               ║
║              │  Calibrated     │                                             ║
║              │  against refs   │                                             ║
║              └────────┬────────┘                                             ║
║                       │                                                      ║
║              ┌────────┴────────┐                                             ║
║              │                 │                                              ║
║         ≥ threshold      < threshold                                         ║
║              │                 │                                              ║
║              ▼                 ▼                                              ║
║   ┌──────────────┐   ┌─────────────────┐                                    ║
║   │  AD LIBRARY  │   │  EDITOR         │                                    ║
║   │              │   │  (Gemini Pro)   │                                    ║
║   │  approved    │   │                 │◄──── weakness diagnosis             ║
║   │  ads + meta  │   │  Surgical fix   │      (which dimension, why)        ║
║   │  + scores    │   │  of weakest     │                                    ║
║   └──────────────┘   │  dimension      │──── max 3 attempts                  ║
║                      │                 │     then escalate                    ║
║                      └────────┬────────┘                                     ║
║                               │ revised ad                                   ║
║                               ▼                                              ║
║                      (back to EVALUATOR)                                     ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                           FEEDBACK LOOPS                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  LOOP 1: Ad-Level (inner)                                                    ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │  generate → evaluate → diagnose weakness → edit → re-evaluate      │     ║
║  │  (max 3 cycles per ad)                                             │     ║
║  └─────────────────────────────────────────────────────────────────────┘     ║
║                                                                              ║
║  LOOP 2: Batch-Level (outer)                                                 ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │  generate batch → evaluate → analyze trends →                      │     ║
║  │  self-heal (adjust prompts if quality drops) →                     │     ║
║  │  ratchet threshold → next batch                                    │     ║
║  └─────────────────────────────────────────────────────────────────────┘     ║
║                                                                              ║
║  LOOP 3: System-Level (meta)                                                 ║
║  ┌─────────────────────────────────────────────────────────────────────┐     ║
║  │  competitive intel → pattern extraction →                          │     ║
║  │  inject patterns into generation → measure improvement             │     ║
║  └─────────────────────────────────────────────────────────────────────┘     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Key Architecture Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Separate `src/llm/`** | All LLM calls go through one client | Token tracking, cost accounting, rate limiting in one place |
| **`models.py` with Pydantic** | Typed data models for everything | Structured LLM output parsing, validation, serialization |
| **Config in YAML, not hardcoded** | `config/` directory | Reproducible runs, easy to tweak thresholds without code changes |
| **`src/` not flat root** | Source code under `src/` | Clean imports, standard packaging, tests outside source |
| **`output/` gitignored** | Generated artifacts excluded from repo | Only code + config + data committed; results are reproducible |
| **Prompts in `prompts.py`** | Separated from logic | Easy to audit, version, and A/B test prompt changes |
| **3 feedback loops** | Ad-level, batch-level, system-level | Each operates at a different timescale with different signals |

---

## Data Flow for a Single Ad

```
Brief → enriched with patterns from Research Module
     → Writer generates 3 variants (Gemini Flash, ~$0.001 each)
     → Evaluator scores all 3 (Gemini Pro, ~$0.003 each)
     → Best variant selected
     → If ≥ 7.0: add to library (cost: ~$0.012)
     → If < 7.0: diagnose weakest dimension
         → Editor rewrites weak parts (Gemini Pro, ~$0.005)
         → Re-evaluate (Gemini Pro, ~$0.003)
         → If ≥ 7.0: add to library (cost: ~$0.020)
         → If still < 7.0: try up to 2 more edits
         → If 3 edits fail: log failure, move on (cost: ~$0.035, wasted)
```

**Total cost per passing ad: ~$0.012-$0.020**
**Cost per failed ad: ~$0.035 (important to track)**
