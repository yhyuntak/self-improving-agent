# Self Improving Agent QA Fixes

## Task Summary

Fix the two important QA findings from the new `self_improving_agent` contract work: stale generated artifacts on `run_id` reuse, and `agent-cycle` instructions that still under-specify artifact-based review.

## Desired Outcome

- a repeated `run_id` cannot leave stale files inside `artifacts/{run_id}/project/`
- `agent-cycle` explicitly tells evaluator and critic to consume generated project artifacts
- regression tests cover the stale-artifact path and the updated orchestration contract
- the repo is ready for `$qa` again without the same findings returning

## In Scope

- fix project output isolation in `agents/self_improving_agent/run.py`
- add a regression test for `run_id` reuse and stale artifact carryover
- align `.codex/skills/agent-cycle/SKILL.md` with the evaluator and critic artifact-review contract
- add one contract-style test or repo check that protects the updated `agent-cycle` wording

## Non-Goals

- do not redesign the whole agent again
- do not add real command execution for `start_command`, `test_command`, or `e2e_command`
- do not fully solve QA handoff completeness in this pass unless it is trivial and local
- do not remove the legacy `simple_prompt_agent` path in this pass

## Design Direction

Treat run isolation as a correctness issue, not a cosmetic cleanup issue.

The safest direction is:

- keep `run_id` override support
- clear or recreate `artifacts/{run_id}/project/` before materializing new files
- make the behavior explicit in tests

Do not rely on timestamp uniqueness alone because manual `--run-id` reuse is already supported.

For orchestration text, make `agent-cycle` explicitly mirror the new evaluator and critic contracts:

- evaluator reads run-history files plus `artifacts/{run_id}/project/`
- critic reads run-history files, `evaluation.json`, plus `artifacts/{run_id}/project/`

This should be fixed in the skill text itself so Main Codex does not have to infer the missing input.

## Test Strategy

Mixed:

- unit-first for the stale-artifact regression in `tests/test_self_improving_agent.py`
- doc/config verification for the `agent-cycle` contract wording
- rerun the focused pytest set that already covers the new agent path

## Task

Close the QA findings by fixing generated artifact isolation and making the orchestration contract explicitly artifact-based.

### AC1

Reusing a `run_id` does not leave stale files inside `artifacts/{run_id}/project/`.

#### TC1

Add a regression test that runs `self_improving_agent` twice with the same `run_id` and verifies old generated files do not remain after the second run.

#### TC2

Run the focused pytest suite and verify the stale-artifact regression passes.

### AC2

`agent-cycle` explicitly instructs evaluator and critic to read generated project artifacts.

#### TC1

Read `.codex/skills/agent-cycle/SKILL.md` and verify the evaluator step lists `artifacts/{run_id}/project/` as an input.

#### TC2

Read `.codex/skills/agent-cycle/SKILL.md` and verify the critic step lists `artifacts/{run_id}/project/` as an input.

#### TC3

Add or update a repo contract test so the skill text regression is less likely to return silently.

### AC3

The focused regression/test pass is green after the fixes.

#### TC1

Run `pytest` for:

- `tests/test_self_improving_agent.py`
- `tests/test_agent_cycle_state.py`
- `tests/test_simple_prompt_agent.py`

#### TC2

Verify no new QA blocker appears in the fixed areas when reviewing the updated diff locally.

## Execution Order

1. Fix run isolation in `agents/self_improving_agent/run.py`.
2. Add the stale-artifact regression test.
3. Align `.codex/skills/agent-cycle/SKILL.md` with artifact-based evaluator and critic inputs.
4. Add a small contract test for the skill wording if needed.
5. Run the focused pytest set.

## Open Risks

- a contract-only test for skill wording may be brittle if over-specified
- the QA handoff omission remains a smaller process issue unless handled in a later pass
- legacy and new agent paths still coexist, so repo language needs continued discipline

## Execute Handoff

- `task_id`: `self-improving-agent-qa-fixes`
- `plan_path`: `/home/yhyuntak/workspace/self-improving-agent/.everything-automate/plans/2026-04-08-self-improving-agent-qa-fixes.md`
- `approval_state`: `approved`
- `execution_unit`: `AC`
- `test_strategy`: `mixed`
- `open_risks`:
  - `skill-contract test may become too brittle if written too narrowly`
  - `legacy and new agent paths still coexist during the transition`
