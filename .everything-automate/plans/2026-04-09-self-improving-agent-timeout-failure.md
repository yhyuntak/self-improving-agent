# Self Improving Agent Timeout Failure Handling

## Task Summary

Make `self_improving_agent` fail fast and leave deterministic failure artifacts when the model call stalls or errors.

## Desired Outcome

- model calls have an explicit timeout
- a stalled or failed model call does not hang forever
- failed runs still write clear failure evidence to `events.jsonl` and `meta.json`
- regression tests prove timeout/failure runs are observable and non-silent

## In Scope

- add configurable request timeout handling to `agents/self_improving_agent/run.py`
- record failure events and failure metadata when run execution fails after `input.json` exists
- add regression coverage for timeout/failure artifact writing
- rerun the focused pytest set for the agent path

## Non-Goals

- do not redesign `agent-cycle`
- do not change evaluator or critic schemas
- do not add command execution for generated projects
- do not remove fallback model support

## Design Direction

Treat provider delay as a run failure, not as indefinite waiting.

Use a small explicit timeout for each model attempt, sourced from config with a safe default.
If model execution or output parsing fails after the run starts:

- append a `run_failed` event
- append a final `run_finished` event with failure status
- write `meta.json` with failure details
- re-raise the error so callers still see a non-zero result

Keep `output.json` success-only.

## Test Strategy

Mixed:

- unit-first for timeout/failure artifact behavior in `tests/test_self_improving_agent.py`
- focused pytest run for the self-improving-agent and related support tests

## Task

Add timeout and failure artifact handling to `self_improving_agent`.

### AC1

Model calls use an explicit timeout instead of waiting forever.

#### TC1

Inspect `agents/self_improving_agent/run.py` and verify the OpenRouter request path passes an explicit timeout value.

#### TC2

Verify timeout configuration has a stable default and can still be overridden from environment.

### AC2

Runs that fail after start leave deterministic failure artifacts.

#### TC1

Add a regression test where the client raises a timeout-like error and verify `events.jsonl` includes `run_failed` and `run_finished` with failure status.

#### TC2

Verify the same regression writes `meta.json` with failure details and does not leave a fake success `output.json`.

### AC3

The focused regression/test pass is green after the fix.

#### TC1

Run `pytest` for:

- `tests/test_self_improving_agent.py`
- `tests/test_agent_cycle_state.py`
- `tests/test_simple_prompt_agent.py`

#### TC2

Review the changed paths and confirm the new failure path is explicit enough that `agent-cycle` can diagnose failed runs without hanging.

## Execution Order

1. Add timeout config and failure artifact helpers in `agents/self_improving_agent/run.py`.
2. Add timeout/failure regression coverage in `tests/test_self_improving_agent.py`.
3. Run the focused pytest set.
4. Hand off to `$qa`.

## Open Risks

- timeout is a tradeoff: too low can create false failures, too high weakens fast feedback
- failure artifacts improve observability but do not by themselves solve provider instability

## Execute Handoff

- `task_id`: `self-improving-agent-timeout-failure`
- `plan_path`: `/home/yhyuntak/workspace/self-improving-agent/.everything-automate/plans/2026-04-09-self-improving-agent-timeout-failure.md`
- `approval_state`: `approved`
- `execution_unit`: `AC`
- `test_strategy`: `mixed`
- `open_risks`:
  - `timeout value may need tuning after real benchmark runs`
  - `provider instability can still fail runs, but now it should fail clearly`
