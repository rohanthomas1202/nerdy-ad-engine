# Nerdy Ad Engine

Autonomous content generation system for Varsity Tutors ad copy. Evaluator-centric architecture with dimension-level diagnosis and targeted repair.

## Setup

```bash
# Clone and install
git clone <repo-url>
cd nerdy-ad-engine
make install

# Configure API key
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Run tests
make test

# Run linter
make lint

# Run pipeline
make run
```

## Architecture

See [architecture.md](architecture.md) for full system architecture and repository structure.

See [phases.md](phases.md) for the phased implementation plan.

## Tech Stack

| Component | Tool |
|-----------|------|
| Language | Python 3.11+ |
| LLM (generation) | Gemini Flash |
| LLM (evaluation) | Gemini Pro |
| Data models | Pydantic v2 |
| Config | YAML |
| Testing | pytest |
| Linting | ruff |
