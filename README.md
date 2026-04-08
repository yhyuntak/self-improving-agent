# Self Improving Agent

This repo now starts from one main project-building agent module.

The Main Codex session is the orchestrator.
It runs the agent by CLI, then local evaluator and critic sub-agents can read the run files and judge what should change next.

## Current Flow

```text
Main Codex
  -> run one agent-cycle
  -> execute self_improving_agent on a fixed benchmark prompt
  -> run evaluator sub-agent to write evaluation.json
  -> run critic sub-agent to write critique.json
  -> diagnose what to improve
  -> report to the user and stop for approval
  -> resume the same cycle after approval
  -> use improve-agent for one bounded change
  -> run tests and close the cycle
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
  state/
    agent-cycles/
  skills/
    agent-cycle/
    diagnose-agent/
    improve-agent/
agents/
  self_improving_agent/
    AGENTS.md
    run.py
    prompts/
benchmarks/
artifacts/
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
OPENROUTER_MODEL=google/gemma-4-31b-it
OPENROUTER_FALLBACK_MODELS=qwen/qwen3.6-plus:free,stepfun/step-3.5-flash:free,nvidia/nemotron-3-super-120b-a12b:free
OPENROUTER_SITE_URL=https://your-site.example
OPENROUTER_APP_NAME=self-improving-agent
```

## Run The Agent

```bash
.venv/bin/python -m agents.self_improving_agent.run "Build a tiny note-taking app." --run-id demo-run
```

Or:

```bash
.venv/bin/self-improving-agent "Build a tiny note-taking app." --run-id demo-run
```

For long benchmark specs, prefer a prompt file:

```bash
.venv/bin/python -m agents.self_improving_agent.run --prompt-file benchmarks/todo-list-project.txt --run-id todo-benchmark
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

And generated project output lands here:

```text
artifacts/{run_id}/project/
```

### File Roles

- `input.json`
  - the user prompt and run metadata at input time
- `output.json`
  - the generated project summary and output metadata
- `events.jsonl`
  - ordered run events
- `meta.json`
  - model and runtime metadata

## Cycle State

Each `agent-cycle` also keeps one resumable state file:

```text
.codex/state/agent-cycles/{cycle_id}.json
```

This file is for orchestration state only.
Run artifacts stay in `runs/{run_id}/`.

## Local Sub-Agents

- `.codex/agents/evaluator`
  - reads run artifacts plus generated project artifacts and writes a structured evaluation
- `.codex/agents/critic`
  - reads run artifacts, generated project artifacts, plus evaluation and writes a structured critique

## Local Skills

- `.codex/skills/agent-cycle`
  - orchestrate the review phase and the apply phase with an approval gate
- `.codex/skills/diagnose-agent`
  - combine run output, evaluation, and critique into one diagnosis
- `.codex/skills/improve-agent`
  - apply approved changes to the agent module
