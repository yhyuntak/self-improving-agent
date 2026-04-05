# Minimal Agent Harness

Small, testable task-agent harness built AC-by-AC.

## Current state

- `scripted` backend: deterministic loop for local development and tests
- `openai` backend: real model-backed action selection through the OpenAI Responses API
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

## Run the OpenAI backend

Set environment variables first:

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_MODEL=gpt-5.4-mini
```

Then run:

```bash
.venv/bin/python -m minimal_agent_harness "Use one tool and then finish" --backend openai
```

The OpenAI backend uses the Responses API and expects the model to return one JSON action at a time.

## Run the benchmark suite

```bash
.venv/bin/python -m minimal_agent_harness.benchmark --tasks-dir benchmarks/tasks --log-root benchmark_runs/latest
```
