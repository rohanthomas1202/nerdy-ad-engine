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
  <img src="https://img.shields.io/badge/tests-62%2B_passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## Overview

Nerdy Ad Engine is an autonomous content generation pipeline built for **Varsity Tutors** SAT test prep advertising. It takes structured ad briefs as input, generates multiple creative variants using Gemini Flash, evaluates each variant across 5 quality dimensions using Gemini Pro, and routes results through a quality gate — all with full cost tracking.

The system follows an **evaluator-centric architecture**: the quality evaluator was built and calibrated *before* the generator, ensuring a proven quality signal exists before scaling content production.

### How It Works

```
                    ┌─────────────────────────────────────────────┐
                    │              PIPELINE FLOW                  │
                    │                                             │
  briefs.yaml ──▶   Brief Interpreter (enrich with brand context) │
                    │         │                                   │
                    │         ▼                                   │
                    │   Variant Strategy (3 diverse approaches)   │
                    │         │                                   │
                    │         ▼                                   │
                    │   Writer (Gemini Flash → structured ad)     │
                    │         │                                   │
                    │         ▼                                   │
                    │   Dimension Scorer (Gemini Pro → 5 scores)  │
                    │         │                                   │
                    │         ▼                                   │
                    │   Quality Gate (≥ 7.0 → approved)           │
                    │       ╱    ╲                                │
                    │      ▼      ▼                               │
                    │  ad_library  failed_ads                     │
                    └─────────────────────────────────────────────┘
```

## Features

- **Multi-variant generation** — 3 diverse ad variants per brief using audience-weighted hook selection (question, statistic, story, empathy, urgency, and more)
- **5-dimension quality evaluation** — Clarity, Value Proposition, Call-to-Action, Brand Voice, and Emotional Resonance — each with calibrated rubrics and weighted scoring
- **Quality gate routing** — Ads scoring ≥ 7.0/10 are approved; below-threshold ads are flagged with their weakest dimension for targeted improvement
- **Config-driven pipeline** — Briefs, brand guidelines, dimensions, model settings, and thresholds all live in YAML configuration
- **Full cost tracking** — Per-request token counting and USD cost accumulation across the entire pipeline
- **Typed data contracts** — Pydantic v2 models for all data structures ensure validated, structured LLM output parsing
- **Rate-limited LLM client** — Built-in retry logic for rate limits and 4-second inter-request throttling

## Demo

<!-- Add screenshots or GIF of pipeline output here -->

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
  Aggregate ............ 7.57  ✓ APPROVED

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
make test    # Run 62+ tests
make lint    # Check code quality with ruff
```

## Usage

### Generate Ads

```bash
make run
```

This processes all briefs in `config/briefs.yaml`, generates 3 variants per brief, evaluates each, and saves results to the `output/` directory.

### Output Files

| File | Description |
|------|-------------|
| `output/ad_library.json` | All approved ads (score ≥ 7.0) with full evaluation details |
| `output/failed_ads.json` | Ads that didn't pass the quality gate |

### Programmatic Usage

```python
from src.main import Pipeline

pipeline = Pipeline()

# Process a single brief
record = pipeline.run_single(brief_id="sat-parent-conversion-01")

# Process all briefs
results = pipeline.run_batch()

# Check costs
print(f"Total cost: ${pipeline.client.total_cost:.4f}")
```

## Project Structure

```
nerdy-ad-engine/
├── config/
│   ├── settings.yaml          # Model config, thresholds, cost rates
│   ├── dimensions.yaml        # 5 evaluation dimensions with rubrics
│   ├── briefs.yaml            # 12 ad briefs (audience, product, goal)
│   └── brand_guidelines.yaml  # Brand voice, tone, audience triggers
├── data/
│   ├── reference_ads.json     # Calibration reference ads (high/mid/low)
│   ├── competitor_ads.json    # Competitive intel (Phase 4)
│   └── patterns/
│       └── taxonomy.json      # Pattern extraction (Phase 4)
├── src/
│   ├── main.py                # Pipeline orchestrator — entry point
│   ├── models.py              # Pydantic data contracts
│   ├── llm/
│   │   ├── client.py          # Unified Gemini client (Flash + Pro)
│   │   └── prompts.py         # Prompt template library
│   ├── generate/
│   │   ├── brief_interpreter.py   # Config-driven brief enrichment
│   │   ├── writer.py              # Ad copy generation
│   │   └── variant_strategy.py    # Diverse approach selection
│   ├── evaluate/
│   │   ├── dimension_scorer.py    # 5-dimension quality scoring
│   │   ├── aggregator.py          # Weighted score aggregation
│   │   ├── calibrator.py          # Evaluator calibration
│   │   └── quality_gate.py        # Pass/fail routing
│   ├── iterate/                   # Phase 3 — feedback loops
│   ├── research/                  # Phase 4 — competitive intel
│   └── analytics/                 # Phase 5 — tracking & self-healing
├── tests/                     # 62+ tests across 13 modules
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
| `AdRecord` | Complete pipeline output — ad + evaluation + metadata + cost |

### Cost Economics

| Operation | Model | Approximate Cost |
|-----------|-------|-----------------|
| Generate 1 ad variant | Gemini Flash | ~$0.0001 |
| Evaluate 1 ad | Gemini Pro | ~$0.006 |
| Full pipeline (1 brief, 3 variants) | Both | ~$0.02 |

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
make test      # Run all tests
make lint      # Run ruff linter
make run       # Execute the pipeline
make clean     # Remove caches and output artifacts
```

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Done | Foundation — models, LLM client, evaluator, calibration |
| **Phase 2** | ✅ Done | Generation loop — brief interpreter, writer, variant strategy, pipeline |
| **Phase 3** | ⏳ Next | Feedback loop — weakness diagnosis, targeted editing, escalation logic |
| **Phase 4** | 📋 Planned | Competitive intelligence — pattern extraction from competitor ads |
| **Phase 5** | 📋 Planned | Analytics & self-healing — quality trends, token economics, auto-calibration |
| **Phase 6** | 📋 Planned | Scale — 100+ ads per run, demo mode, decision logging |

See [phases.md](phases.md) for detailed phase specifications and success criteria.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Author

**Rohan Thomas** — [GitHub](https://github.com/rohanthomas1202)

---

<p align="center">
  Built with Gemini 2.5 &middot; Evaluated before generated &middot; Quality over quantity
</p>
