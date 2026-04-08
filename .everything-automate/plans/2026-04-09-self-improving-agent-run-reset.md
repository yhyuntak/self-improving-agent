# Self Improving Agent Run Reset

## Task Summary

Fix the remaining QA issue in `self_improving_agent`: reusing a `run_id` must not leak stale run-history files into the next review cycle.

## Desired Outcome

- reusing a `run_id` fully replaces the old run state
- `runs/{run_id}/` does not keep stale `events.jsonl`, `output.json`, `meta.json`, `evaluation.json`, or `critique.json`
- `artifacts/{run_id}/project/` stays aligned with the fresh run only
- regression tests prove that a second run with the same `run_id` cannot expose first-run evidence

## In Scope

- define and implement full run-state reset semantics for reused `run_id`
- update `agents/self_improving_agent/run.py` to reset run and artifact roots before writing new files
- add regression coverage for stale run-history leakage on reused `run_id`
- rerun the focused pytest set for the self-improving-agent path

## Non-Goals

- do not redesign the agent-cycle flow again
- do not add execution of `start_command`, `test_command`, or `e2e_command`
- do not remove `run_id` override support
- do not change evaluator or critic output schema in this pass

## Design Direction

Treat reused `run_id` as full replacement, not partial cleanup.

The implementation should:

- delete and recreate `runs/{run_id}/`
- delete and recreate `artifacts/{run_id}/`
- only then write fresh `input.json`, `events.jsonl`, `output.json`, and `meta.json`

This is stronger than clearing `events.jsonl` alone and protects against stale success files if a rerun fails midway.

Keep the contract simple:

- unique `run_id` remains the normal path
- reused `run_id` is allowed
- reused `run_id` means the old run is fully replaced

## Test Strategy

Mixed:

- unit-first for reused-`run_id` reset behavior in `tests/test_self_improving_agent.py`
- focused regression run with `pytest` on the self-improving-agent test set and related support tests

## Task

Close the remaining QA gap by making reused `run_id` a full reset boundary.

### AC1

Reusing a `run_id` fully clears stale run-history files before the next run begins.

#### TC1

Add a regression that runs `self_improving_agent` twice with the same `run_id` and verifies the second run's `events.jsonl` contains only the second run's events.

#### TC2

Extend the reused-`run_id` regression to verify stale `output.json`, `meta.json`, and generated project files from the first run do not survive the second run.

### AC2

The implementation resets both run history and generated artifacts before new outputs are written.

#### TC1

Inspect `agents/self_improving_agent/run.py` and verify the reset happens before any fresh event append or output write.

#### TC2

Verify the reset behavior does not remove the normal successful outputs of the second run.

### AC3

The focused regression/test pass is green after the fix.

#### TC1

Run `pytest` for:

- `tests/test_self_improving_agent.py`
- `tests/test_agent_cycle_state.py`
- `tests/test_simple_prompt_agent.py`

#### TC2

Review the changed paths and confirm the run-reset contract is explicit enough that `$qa` should not rediscover the same stale-evidence issue.

## Execution Order

1. Update `agents/self_improving_agent/run.py` to reset full run state on reused `run_id`.
2. Expand the reused-`run_id` regression in `tests/test_self_improving_agent.py`.
3. Run the focused pytest set.
4. Hand off to `$qa`.

## Open Risks

- full directory reset is destructive by design, so this contract must stay explicit in repo docs and future tests
- time-based `run_id` generation is still probabilistic under true concurrency, even though manual reuse is now handled cleanly

## Execute Handoff

- `task_id`: `self-improving-agent-run-reset`
- `plan_path`: `/home/yhyuntak/workspace/self-improving-agent/.everything-automate/plans/2026-04-09-self-improving-agent-run-reset.md`
- `approval_state`: `approved`
- `execution_unit`: `AC`
- `test_strategy`: `mixed`
- `open_risks`:
  - `full reset is intentionally destructive for reused run_id`
  - `default run_id is still time-based under true concurrency`
