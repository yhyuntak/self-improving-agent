# Self Improving Agent

This repo now starts from one simple agent module.

The Main Codex session is the orchestrator.
It runs the agent by CLI, then local evaluator and critic sub-agents can read the run files and judge what should change next.

## Current Flow

```text
Main Codex
  -> run simple_prompt_agent
  -> inspect run artifacts
  -> use evaluator sub-agent
  -> use critic sub-agent
  -> diagnose what to improve
  -> improve the agent module
```

There is no loop in the agent itself yet.
There is no tool use yet.
Everything starts from one prompt and one answer.

## Repo Shape

```text
.codex/
  agents/
    evaluator/
    critic/
  skills/
    diagnose-agent/
    improve-agent/
agents/
  simple_prompt_agent/
    AGENTS.md
    run.py
    prompts/
runs/
tests/
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
```

## Environment

Example `.env`:

```bash
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=qwen/qwen3.6-plus:free
OPENROUTER_FALLBACK_MODELS=stepfun/step-3.5-flash:free,nvidia/nemotron-3-super-120b-a12b:free,google/gemma-4-31b-it
OPENROUTER_SITE_URL=https://your-site.example
OPENROUTER_APP_NAME=self-improving-agent
```

## Run The Agent

```bash
.venv/bin/python -m agents.simple_prompt_agent.run "Draft a tiny concept note for a note-taking app." --run-id demo-run
```

Or:

```bash
.venv/bin/simple-prompt-agent "Draft a tiny concept note for a note-taking app." --run-id demo-run
```

## Run Artifacts

Each run writes:

```text
runs/{run_id}/
  input.json
  output.json
  events.jsonl
  meta.json
```

### File Roles

- `input.json`
  - the user prompt and run metadata at input time
- `output.json`
  - the final agent answer as JSON
- `events.jsonl`
  - ordered run events
- `meta.json`
  - model and runtime metadata

## Local Sub-Agents

- `.codex/agents/evaluator`
  - reads run artifacts and writes a structured evaluation
- `.codex/agents/critic`
  - reads run artifacts plus evaluation and writes a structured critique

## Local Skills

- `.codex/skills/diagnose-agent`
  - combine run output, evaluation, and critique into one diagnosis
- `.codex/skills/improve-agent`
  - apply approved changes to the agent module
