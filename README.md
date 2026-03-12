<p align="center">
  <h1 align="center">Nerdy Ad Engine</h1>
  <p align="center">
    Autonomous ad copy generation system with evaluator-centric quality control
    <br />
    <em>Generate, evaluate, and iteratively improve Facebook/Instagram ad copy at scale</em>
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/LLM-Gemini_2.5-orange?logo=google&logoColor=white" alt="Gemini 2.5">
  <img src="https://img.shields.io/badge/models-Pydantic_v2-e92063?logo=pydantic&logoColor=white" alt="Pydantic v2">
  <img src="https://img.shields.io/badge/tests-123_passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## Overview

Nerdy Ad Engine is an autonomous content generation pipeline built for **Varsity Tutors** SAT test prep advertising. It takes structured ad briefs as input, generates multiple creative variants using Gemini Flash, evaluates each variant across 5 quality dimensions using Gemini Pro, iteratively improves failing ads through targeted editing, and routes results through a quality gate — all with full cost tracking and self-healing analytics.

The system follows an **evaluator-centric architecture**: the quality evaluator was built and calibrated *before* the generator, ensuring a proven quality signal exists before scaling content production.

### How It Works

```
  briefs.yaml ──▶ Brief Interpreter (enrich with brand + competitive context)
                          │
                          ▼
                  Variant Strategy (3 diverse approaches)
                          │
                          ▼
                  Writer (Gemini Flash → structured ad)
                          │
                          ▼
                  Dimension Scorer (Gemini Pro → 5 scores)
                          │
                          ▼
                  Quality Gate (≥ 7.0 → approved)
                        ╱    ╲
                  ✓ Pass      ✗ Fail
                    │           │
                    ▼           ▼
              ad_library    Diagnose → Edit → Re-evaluate (up to 3x)
                                │
                          ╱          ╲
                    Rescued        Abandoned
                  (approved)     (failed_ads)
```

## Features

- **Multi-variant generation** — 3 diverse ad variants per brief using audience-weighted hook selection (question, statistic, story, empathy, urgency, and more)
- **5-dimension quality evaluation** — Clarity, Value Proposition, Call-to-Action, Brand Voice, and Emotional Resonance — each with calibrated rubrics and weighted scoring
- **Quality gate routing** — Ads scoring >= 7.0/10 are approved; below-threshold ads enter the iteration loop
- **Targeted iteration** — Dimension-level weakness diagnosis, surgical editing with preservation rules, and 3-strike escalation (continue → escalate → abandon)
- **Competitive intelligence** — Pattern extraction from 20+ competitor ads, taxonomy of hooks/CTAs/angles integrated into generation
- **Analytics & self-healing** — Quality trend tracking, regression detection, auto-threshold ratcheting, cost-per-ad and quality-per-dollar metrics
- **Error resilience** — Single ad failures don't crash the batch; errors are logged with full context
- **Config-driven pipeline** — Briefs, brand guidelines, dimensions, model settings, and thresholds all live in YAML configuration
- **Full cost tracking** — Per-request token counting and USD cost accumulation across the entire pipeline
- **Typed data contracts** — Pydantic v2 models for all data structures ensure validated, structured LLM output parsing
- **Demo mode** — Quick 3-5 minute walkthrough showcasing the full pipeline

## Demo

<details>
<summary>Sample Approved Ad (score: 7.57/10)</summary>

```
Brief:    sat-parent-conversion-01
Headline: "Stress-Free SAT Prep. Real Results."
Primary:  "Feeling overwhelmed by college applications..."
CTA:      Get Started

Dimension Scores:
  Clarity .............. 7.8
  Value Proposition .... 7.5
  Call-to-Action ....... 5.5
  Brand Voice .......... 8.5
  Emotional Resonance .. 8.8
  ─────────────────────────
  Aggregate ............ 7.57  APPROVED

Cost: $0.006
```

</details>

## Installation

### Prerequisites

- Python 3.11+
- A [Google AI Studio](https://aistudio.google.com/) API key (Gemini)

### Setup

```bash
# Clone the repository
git clone https://github.com/rohanthomas1202/nerdy-ad-engine.git
cd nerdy-ad-engine

# Install dependencies
make install

# Configure your API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=<your-key>
```

### Verify Installation

```bash
make test    # Run 123 tests
make lint    # Check code quality with ruff
```

## Usage

### CLI Commands

```bash
# Generate ads from all briefs (35 briefs x 3 variants = 105 ads)
python3 -m src.main

# Limit the number of ads generated
python3 -m src.main --count 30

# Run multiple cycles with analytics between each
python3 -m src.main --cycles 5

# Full production run (105 ads x 7 cycles)
python3 -m src.main --count 120 --cycles 7

# Demo mode — quick walkthrough
python3 -m src.main --demo

# Competitive intelligence research
python3 -m src.main --research

# Custom output directory and seed
python3 -m src.main --output-dir results/ --seed 99
```

### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--count N` | all briefs | Maximum number of ads to generate |
| `--cycles N` | 1 | Number of generation cycles |
| `--seed N` | 42 | Random seed for reproducibility |
| `--demo` | off | Run in demo mode (quick walkthrough) |
| `--research` | off | Run competitive intelligence research |
| `--output-dir` | `output/` | Output directory for results |
| `--port` | 8020 | Dashboard port (range: 8020-8030) |

### Output Files

| File | Description |
|------|-------------|
| `output/ad_library.json` | Approved ads with full evaluation details |
| `output/failed_ads.json` | Failed ads with iteration history and error messages |
| `output/quality_trends.png` | Per-dimension quality trends across cycles |
| `output/cost_dashboard.png` | Cost breakdown and quality-per-dollar metrics |
| `output/experiment_log.json` | Per-cycle experiment log with metrics |
| `output/calibration_report.json` | Evaluator calibration alignment report |

### Programmatic Usage

```python
from src.main import Pipeline

pipeline = Pipeline()

# Process all briefs
results = pipeline.run_batch()

# Run with analytics across multiple cycles
results = pipeline.run_cycles(num_cycles=5)

# Check costs
print(f"Total cost: ${pipeline._client.total_cost:.4f}")
```

## Project Structure

```
nerdy-ad-engine/
├── config/
│   ├── settings.yaml          # Model config, thresholds, cost rates
│   ├── dimensions.yaml        # 5 evaluation dimensions with rubrics
│   ├── briefs.yaml            # 35 ad briefs (audience, product, goal)
│   └── brand_guidelines.yaml  # Brand voice, tone, audience triggers
├── data/
│   ├── reference_ads.json     # Calibration reference ads (high/mid/low)
│   ├── competitor_ads.json    # 20+ competitor ads for analysis
│   └── patterns/
│       └── taxonomy.json      # Extracted pattern taxonomy
├── src/
│   ├── main.py                # Pipeline orchestrator — entry point
│   ├── demo.py                # Demo mode walkthrough
│   ├── models.py              # Pydantic data contracts
│   ├── llm/
│   │   ├── client.py          # Unified Gemini client (Flash + Pro)
│   │   └── prompts.py         # Prompt template library
│   ├── generate/
│   │   ├── brief_interpreter.py   # Config-driven brief enrichment
│   │   ├── writer.py              # Ad copy generation (Gemini Flash)
│   │   └── variant_strategy.py    # Diverse approach selection
│   ├── evaluate/
│   │   ├── dimension_scorer.py    # 5-dimension scoring (Gemini Pro)
│   │   ├── aggregator.py          # Weighted score aggregation
│   │   ├── calibrator.py          # Evaluator calibration
│   │   └── quality_gate.py        # Pass/fail routing
│   ├── iterate/
│   │   ├── weakness_diagnostician.py  # Dimension-level diagnosis
│   │   ├── targeted_editor.py        # Surgical editing (Gemini Pro)
│   │   └── escalation.py             # 3-strike escalation logic
│   ├── research/
│   │   ├── competitor_analyzer.py     # Competitor ad analysis
│   │   ├── reference_analyzer.py      # Performance correlation
│   │   └── pattern_taxonomy.py        # Pattern extraction & storage
│   └── analytics/
│       ├── quality_tracker.py     # Per-dimension trend tracking
│       ├── token_tracker.py       # Cost analytics & quality-per-dollar
│       ├── quality_ratchet.py     # Auto-threshold ratcheting
│       ├── self_healer.py         # Regression detection & diagnosis
│       └── experiment_logger.py   # Structured experiment history
├── docs/
│   ├── decision_log.md        # Engineering decisions & trade-offs
│   └── limitations.md         # Honest limitations assessment
├── tests/                     # 123 tests across 25 modules
├── output/                    # Generated artifacts
├── Makefile                   # Build commands
├── requirements.txt           # Python dependencies
├── architecture.md            # System architecture deep-dive
└── phases.md                  # Phased implementation roadmap
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google AI Studio API key | Yes |

### Key Settings (`config/settings.yaml`)

| Setting | Default | Description |
|---------|---------|-------------|
| `quality_threshold` | `7.0` | Minimum aggregate score for approval |
| `max_edit_attempts` | `3` | Max iteration attempts per ad |
| `variants_per_brief` | `3` | Number of variants per brief |
| `generation_model` | `gemini-2.5-flash` | Model for ad copy generation |
| `evaluation_model` | `gemini-2.5-pro` | Model for quality evaluation |
| `generation_temperature` | `0.8` | Creativity level for generation |
| `evaluation_temperature` | `0.1` | Determinism level for evaluation |

### Evaluation Dimensions (`config/dimensions.yaml`)

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Clarity | 0.20 | Can the reader grasp the offer in < 5 seconds? |
| Value Proposition | 0.25 | Are benefits compelling and specific? |
| Call-to-Action | 0.20 | Is the next step clear, urgent, and low-friction? |
| Brand Voice | 0.15 | Does it match the empowering, approachable tone? |
| Emotional Resonance | 0.20 | Does it connect with the audience's feelings? |

## Core Components

### LLM Client

Unified interface for all Gemini API interactions with automatic cost tracking, retry logic, and rate limiting.

```python
client = GeminiClient()
text, usage = client.generate(prompt, model_type="flash", temperature=0.8)
structured, usage = client.generate_structured(prompt, response_type=AdCopy)
```

### Data Models

All pipeline data flows through Pydantic v2 models:

| Model | Purpose |
|-------|---------|
| `Brief` | Input ad brief (audience, product, campaign goal) |
| `AdCopy` | Generated ad (primary text, headline, description, CTA) |
| `DimensionScore` | Single dimension evaluation (score, rationale, confidence) |
| `EvaluationResult` | Full 5-dimension evaluation with aggregate score |
| `AdRecord` | Complete pipeline output — ad + evaluation + iteration history + cost |
| `Diagnosis` | Dimension-level weakness diagnosis for targeted editing |
| `ExperimentEntry` | Structured experiment log entry with before/after metrics |

### Cost Economics

| Operation | Model | Approximate Cost |
|-----------|-------|-----------------|
| Generate 1 ad variant | Gemini Flash | ~$0.0001 |
| Evaluate 1 ad | Gemini Pro | ~$0.006 |
| Full pipeline (1 brief, 3 variants) | Both | ~$0.02 |
| Full production run (105 ads, 7 cycles) | Both | ~$1-3 |

## Documentation

- [Architecture](architecture.md) — System architecture deep-dive
- [Phases](phases.md) — Phased implementation roadmap (all 6 phases complete)
- [Decision Log](docs/decision_log.md) — Engineering decisions, trade-offs, and failed experiments
- [Limitations](docs/limitations.md) — Honest assessment of known limitations and future directions

## Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes and add tests
4. Run the test suite (`make test`) and linter (`make lint`)
5. Commit your changes (`git commit -m 'Add your feature'`)
6. Push to your branch (`git push origin feature/your-feature`)
7. Open a Pull Request

### Development Commands

```bash
make install   # Install dependencies
make test      # Run all 123 tests
make lint      # Run ruff linter
make run       # Execute the pipeline
make clean     # Remove caches and output artifacts
```

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | Done | Foundation — models, LLM client, evaluator, calibration |
| **Phase 2** | Done | Generation loop — brief interpreter, writer, variant strategy, pipeline |
| **Phase 3** | Done | Feedback loop — weakness diagnosis, targeted editing, escalation logic |
| **Phase 4** | Done | Competitive intelligence — pattern extraction from competitor ads |
| **Phase 5** | Done | Analytics & self-healing — quality trends, token economics, auto-ratchet |
| **Phase 6** | Done | Scale & polish — 100+ ads, demo mode, decision log, error resilience |

See [phases.md](phases.md) for detailed phase specifications and success criteria.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Author

**Rohan Thomas** — [GitHub](https://github.com/rohanthomas1202)

---

<p align="center">
  Built with Gemini 2.5 · Evaluated before generated · Quality over quantity
</p>
