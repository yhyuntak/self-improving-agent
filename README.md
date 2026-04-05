# Minimal Agent Harness

Small, testable task-agent harness built AC-by-AC.

## Current state

- `scripted` backend: deterministic loop for local development and tests
- `openrouter` backend: real model-backed action selection through OpenRouter
- core tools: `echo`, `list_files`, `read_file`, `write_file`, `run_shell`
- verifier: blocks finish when the run does not satisfy the minimum completion rules
- tiny benchmark suite under `benchmarks/tasks/`

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Run the scripted backend

```bash
.venv/bin/python -m minimal_agent_harness "demo instruction" --backend scripted
```

## Run the OpenRouter backend

Create a `.env` file first:

```bash
cp .env.example .env
```

Example `.env` values:

```bash
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=qwen/qwen3.6-plus:free
OPENROUTER_FALLBACK_MODELS=stepfun/step-3.5-flash:free,nvidia/nemotron-3-super-120b-a12b:free,google/gemma-4-31b-it
# Optional attribution headers from OpenRouter docs
OPENROUTER_SITE_URL=https://your-site.example
OPENROUTER_APP_NAME=minimal-agent-harness
```

Then run:

```bash
.venv/bin/python -m minimal_agent_harness "Use one tool and then finish" --backend openrouter
```

The harness auto-loads `.env` if it exists. The OpenRouter backend uses the OpenAI Python SDK against OpenRouter's `/api/v1` base URL and expects the model to return one JSON action at a time.

Fallbacks are tried by the harness in strict priority order. The current default shape is:

1. primary free model
2. additional free fallbacks
3. paid fallback only after the free chain is exhausted

## Run the benchmark suite

```bash
.venv/bin/python -m minimal_agent_harness.benchmark --tasks-dir benchmarks/tasks --log-root benchmark_runs/latest
```
