# Agent Cycle Redesign

## Task Summary

Reset `agent-cycle` so it is a real orchestration skill for one full `simple_prompt_agent` improvement loop.

## Desired Outcome

- `agent-cycle` runs a fixed benchmark prompt through `simple_prompt_agent`
- `agent-cycle` uses the evaluator sub-agent to produce `evaluation.json`
- `agent-cycle` uses the critic sub-agent to produce `critique.json`
- Main Codex turns those artifacts into one diagnosis and reports it to the user
- the cycle stops and waits for user approval before any code change
- after approval, the same cycle resumes, runs `improve-agent`, runs tests, and reports the result
- cycle state is stored so the approval step can resume cleanly in a later turn

## In Scope

- rewrite `.codex/skills/agent-cycle/SKILL.md`
- define one durable cycle state artifact and its fields
- define the two phases: `review` and `apply`
- define who is responsible for each step in the loop
- update docs that currently imply Main Codex writes review artifacts directly
- add or update tests for any new helper code that supports cycle state or path handling

## Non-Goals

- do not change `simple_prompt_agent` output schema in this task
- do not add tool use to `simple_prompt_agent`
- do not build an automatic infinite loop
- do not add a benchmark suite manager
- do not turn evaluator or critic into plain helper scripts
- do not rerun the benchmark at the end of the apply phase in the same loop

## Design Direction

`agent-cycle` should be a resumable orchestration skill, not a hidden implementation worker.

Use this split of responsibility:

- `simple_prompt_agent`
  - creates one fresh run from one fixed benchmark prompt
- evaluator sub-agent
  - reads the run artifacts from disk
  - writes `evaluation.json`
- critic sub-agent
  - reads the run artifacts and `evaluation.json`
  - writes `critique.json`
- Main Codex
  - verifies artifact completeness
  - reads the review artifacts
  - writes the final diagnosis in the user-facing report
  - manages the approval gate
- `improve-agent`
  - applies one approved bounded change only after approval

Use a two-phase contract:

- `review`
  - freeze benchmark prompt
  - create fresh run
  - run evaluator sub-agent
  - run critic sub-agent
  - synthesize diagnosis
  - report and stop in `awaiting_approval`
- `apply`
  - resume the saved cycle state
  - read the approved diagnosis
  - run `improve-agent`
  - run relevant tests
  - report what changed
  - stop in `improved`

Add one small cycle state artifact so approval can resume in a later turn without guessing.

Recommended state path:

- `.codex/state/agent-cycles/{cycle_id}.json`

Minimum state fields:

- `cycle_id`
- `benchmark_prompt_path`
- `run_id`
- `run_dir`
- `evaluation_path`
- `critique_path`
- `diagnosis`
- `approved_change`
- `status`
- `created_at`
- `updated_at`

Allowed `status` values:

- `review_running`
- `awaiting_approval`
- `approved`
- `apply_running`
- `improved`
- `failed`

Keep review artifacts in `runs/{run_id}/`.
Keep cycle control state outside `runs/` so old run artifacts stay immutable.

If helper code is needed, keep it small and mechanical.
Good examples:

- cycle id generation
- state file read and write
- path validation

Do not move evaluator, critic, or diagnosis judgment into helper code.

## Test Strategy

Mixed:

- unit-first for any helper code that manages cycle state or path validation
- repo contract checks for required skill text and state path rules when practical
- manual end-to-end verification for the orchestration flow because the real evaluator and critic are agent-driven

## Task

Reset `agent-cycle` into a two-phase orchestration contract that uses real evaluator and critic sub-agents, persists cycle state, and enforces the approval gate before improvement.

### AC1

`agent-cycle` clearly says that evaluator and critic must run as sub-agents, not as direct Main Codex writing steps.

#### TC1

Read `.codex/skills/agent-cycle/SKILL.md` and verify the review phase names:

- `simple_prompt_agent`
- evaluator sub-agent
- critic sub-agent
- Main Codex diagnosis and reporting

#### TC2

Read `.codex/skills/agent-cycle/SKILL.md` and verify it no longer instructs Main Codex to directly author `evaluation.json` or `critique.json` as the default path.

### AC2

The cycle contract is resumable across turns through one explicit state artifact.

#### TC1

Read the plan implementation and confirm a documented state path exists at `.codex/state/agent-cycles/{cycle_id}.json`.

#### TC2

Confirm the documented state fields are enough to resume from `awaiting_approval` without guessing run paths or diagnosis text.

### AC3

The approval gate is explicit and cleanly separates the `review` phase from the `apply` phase.

#### TC1

Read `.codex/skills/agent-cycle/SKILL.md` and verify the review phase ends with report plus `awaiting_approval`.

#### TC2

Read `.codex/skills/agent-cycle/SKILL.md` and verify the apply phase starts only after approval and routes the change through `improve-agent`.

#### TC3

Verify the plan and docs state that benchmark rerun is not part of the same apply phase by default.

### AC4

Repo docs and supporting code match the new contract closely enough that `$execute` does not have to guess.

#### TC1

Read `README.md` and verify the end-to-end loop names real evaluator and critic agent usage plus the approval stop.

#### TC2

If helper code is added, run its unit tests and confirm they cover state creation, state resume, and invalid path or invalid status handling.

#### TC3

Run the existing `tests/test_simple_prompt_agent.py` suite to confirm the redesign work does not break current runner behavior.

## Execution Order

1. Rewrite `.codex/skills/agent-cycle/SKILL.md` around the two-phase orchestration contract.
2. Add the minimal cycle state support surface if the skill text alone would force guessing.
3. Update `README.md` so it describes the real orchestration path.
4. Add or update tests for any helper code.
5. Run the relevant test set.

## Open Risks

- skill text alone may still be too soft if cycle state handling is left fully implicit
- sub-agent orchestration is harder to test automatically than local helper code
- the repo already has dirty edits around `agent-cycle`, so execute must align them instead of layering another partial contract on top

## Execute Handoff

- `task_id`: `agent-cycle-redesign`
- `plan_path`: `/home/yhyuntak/workspace/self-improving-agent/.everything-automate/plans/2026-04-08-agent-cycle-redesign.md`
- `approval_state`: `approved`
- `execution_unit`: `AC`
- `test_strategy`: `mixed`
- `open_risks`:
  - `state contract may stay implicit unless helper support is added`
  - `sub-agent flow still needs manual end-to-end verification`
