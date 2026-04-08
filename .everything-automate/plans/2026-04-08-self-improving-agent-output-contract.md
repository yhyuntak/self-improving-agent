# Self Improving Agent Output Contract

## Task Summary

Shift the repo from a text-only `simple_prompt_agent` into a project-building `self_improving_agent` direction with a real output directory contract.

## Desired Outcome

- the primary agent is renamed toward `self_improving_agent`
- the system prompt tells the agent that project outputs must land in `artifacts/{run_id}/project/`
- the run contract is no longer judged only by `final_answer`
- evaluator and critic look at the generated project output, not only the text response
- the loop starts judging success by generated artifacts, runnable setup, and tests, with E2E as the ideal end state

## In Scope

- rename direction from `simple_prompt_agent` to `self_improving_agent`
- define `artifacts/{run_id}/project/` as the generated project output path
- rewrite the agent system prompt around project generation instead of answer-only behavior
- update the run artifact contract so generated project location is part of the run record
- update evaluator and critic inputs so they inspect generated project artifacts
- update docs and tests for the new direction

## Non-Goals

- do not fully solve autonomous code generation quality in one step
- do not design an unlimited benchmark suite
- do not require perfect E2E on the first implementation pass
- do not add broad multi-agent build orchestration beyond what the current loop needs
- do not keep the old text-only benchmark expectations as the main success signal

## Design Direction

Treat the agent as a project builder, not a pure answer generator.

The important contract change is:

- prompt asks for a project to be created
- agent output must point to real generated files
- success is judged from generated artifacts first

Use this output path:

- `artifacts/{run_id}/project/`

Keep run history artifacts separate:

- `runs/{run_id}/input.json`
- `runs/{run_id}/output.json`
- `runs/{run_id}/events.jsonl`
- `runs/{run_id}/meta.json`

Recommended direction for `output.json`:

- keep `final_answer` only if still useful as a summary
- add generated output location fields so downstream review does not guess

At minimum, the new run contract should let review agents answer:

- where the generated project lives
- whether files were created
- whether the project can start
- whether tests ran
- whether E2E ran

The system prompt should stop framing the agent as a one-pass answer writer.
It should frame the agent as a project-building worker whose job is to create output under the required artifact path and report what it created.

Evaluator and critic should expand their review inputs beyond text:

- generated project directory under `artifacts/{run_id}/project/`
- any test results written into the run or artifact area
- the run summary in `output.json`

Success direction should be C-first:

- files created
- runnable project
- tests passing
- E2E passing when available

But implementation should still be incremental.
The first pass only needs the contracts and code shape to move toward that target cleanly.

## Test Strategy

Mixed:

- unit-first for helper code and path contract changes
- integration-first for run artifact generation and artifact-path recording
- manual verification for the first generated project run
- web E2E as a target contract, not a guaranteed first-pass automated gate

## Task

Redesign the repo so the agent is evaluated as a project builder with outputs under `artifacts/{run_id}/project/`, not as a text-only answer generator.

### AC1

The primary agent contract is renamed and reframed around project generation.

#### TC1

Read the agent module docs and verify the agent is described as a project-building agent rather than a one-pass answer-only agent.

#### TC2

Read the system prompt and verify it explicitly names the required generated output location contract.

### AC2

The run artifact contract records where generated project output lives.

#### TC1

Read the run implementation and verify `artifacts/{run_id}/project/` is the documented or created output path.

#### TC2

Read `output.json` contract changes and verify a reviewer can locate generated artifacts without guessing.

#### TC3

Run a smoke execution and verify the run writes both run-history artifacts and the generated project location record.

### AC3

Evaluation logic is shifted from answer-only review to generated-artifact review.

#### TC1

Read evaluator instructions and verify they include generated project artifacts as review inputs.

#### TC2

Read critic instructions and verify they include generated project artifacts as review inputs.

#### TC3

Confirm the evaluation success language checks for generated files, runnable setup, tests, and E2E direction rather than only text quality.

### AC4

Repo docs and tests match the new project-building direction closely enough that execution does not have to guess.

#### TC1

Read `README.md` and verify it explains the generated output path and the new agent purpose.

#### TC2

Run relevant tests and add missing ones for output path creation and output metadata recording.

#### TC3

Run one smoke scenario and confirm the repo now judges the result from generated artifacts, not only the prose response.

## Execution Order

1. Rename and reframe the agent contract.
2. Add the generated output directory contract to the run path logic and output schema.
3. Rewrite the system prompt around project creation.
4. Update evaluator and critic review inputs.
5. Update docs and tests.
6. Run smoke verification.

## Open Risks

- renaming the module may touch more files than expected
- generated project execution and test passing may need more than one iteration to become stable
- the current codebase is still optimized for text output, so the first pass should prioritize clear contracts over ambitious automation

## Execute Handoff

- `task_id`: `self-improving-agent-output-contract`
- `plan_path`: `/home/yhyuntak/workspace/self-improving-agent/.everything-automate/plans/2026-04-08-self-improving-agent-output-contract.md`
- `approval_state`: `approved`
- `execution_unit`: `AC`
- `test_strategy`: `mixed`
- `open_risks`:
  - `rename scope may be wider than expected`
  - `artifact-first evaluation may require multiple follow-up loops to stabilize`
