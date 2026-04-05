---
status: in_progress
created: 2026-04-05
slug: minimal-agent-harness
test-command: .venv/bin/pytest -q
---

# Plan: minimal-agent-harness

## Requirements

### Context
- The repository is starting from an empty state.
- The goal is to build a small task-oriented agent harness in controllable steps.
- Execution must be gated so only one AC is implemented and tested at a time.

### What
- Create a minimal runnable agent harness first.
- Add tools, verification, benchmark tasks, and self-improvement only after earlier ACs pass.

### Why
- A small, testable base keeps the project understandable and reduces drift.
- AC-by-AC validation makes regressions and learning signals easier to isolate.

### Scope
- In: git-initialized workspace, plan file, AC-1 implementation, AC-1 tests
- Out: AC-2 and later implementation, real model-provider integration, self-improvement loop

## Brain Update

- none

## AC List

- [x] AC-1: Build a minimal runnable harness with a CLI entrypoint, a loop-capable runner, and a sample backend that performs at least one tool call before finishing.
  - TC: Running the sample CLI command completes successfully and prints a final response.
  - TC: The run writes a structured log that includes at least one tool-call event and one finish event.
- [x] AC-2: Add a small-model-friendly core toolset beyond the sample tool.
  - TC: Each tool can be exercised independently through tests.
  - TC: Tool failures return concise, actionable errors.
- [x] AC-3: Add a verification step before the harness can finish.
  - TC: The verifier blocks an intentionally incorrect result.
  - TC: The verifier allows a correct result.
- [ ] AC-4: Add a tiny deterministic benchmark task suite.
  - TC: All benchmark tasks run from one command.
  - TC: The run reports pass/fail or score per task.
- [ ] AC-5: Add a minimal experiment runner for baseline-vs-variant comparison.
  - TC: Two harness variants can be executed against the same task suite.
  - TC: Results are persisted to a log file for comparison.
- [ ] AC-6: Add a constrained first-pass self-improvement loop.
  - TC: The loop can compare a baseline and a modified variant automatically.
  - TC: Worse-performing variants are not promoted.

## Implementation Order

1. [Sequential] AC-1 -> `.codex/plans/`, `pyproject.toml`, `src/`, `tests/`
2. [Sequential] AC-2 -> `src/`, `tests/`
3. [Sequential] AC-3 -> `src/`, `tests/`
4. [Sequential] AC-4 -> `benchmarks/`, `tests/`
5. [Sequential] AC-5 -> `src/`, `tests/`
6. [Sequential] AC-6 -> `src/`, `tests/`

## Test Plan

- Run `pytest -q` for AC-level verification.
- Run the sample CLI command used by AC-1 and inspect the emitted log file.
