---
name: agent-cycle
description: "Run one full self_improving_agent improvement cycle with real evaluator and critic sub-agents, an approval gate, and resumable cycle state."
argument-hint: "<benchmark prompt file or prompt source>"
---

# agent-cycle

Use this when the user wants one end-to-end loop, not separate manual steps.

## Goal

Run one full cycle for `self_improving_agent`:

1. execute the agent on one fixed benchmark prompt
2. run the evaluator sub-agent to write `evaluation.json`
3. run the critic sub-agent to write `critique.json`
4. produce one small diagnosis
5. report the result to the user
6. if the user approves, apply one bounded improvement

## Inputs

Prefer one stable benchmark prompt file outside `runs/`.

Good examples:

- `benchmarks/todo-list-project.txt`
- another plain text or markdown file with the full benchmark spec

Do not use an old `runs/{run_id}/input.json` as the long-term source of truth unless the user explicitly asks for that.

## Main Contract

`agent-cycle` is the orchestrator.

It does not directly replace the worker roles inside the loop.

Use this split of responsibility:

- `self_improving_agent`
  - creates one fresh run from one fixed benchmark prompt
- evaluator sub-agent
  - reads run artifacts from disk
  - writes `runs/{run_id}/evaluation.json`
- critic sub-agent
  - reads run artifacts plus `evaluation.json`
  - writes `runs/{run_id}/critique.json`
- Main Codex
  - checks that each artifact exists
  - reads the run, evaluation, and critique
  - writes one short diagnosis in the user-facing report
  - manages the approval gate
- `improve-agent`
  - applies one approved bounded change after approval

## Cycle State

This skill must keep explicit cycle state at:

- `.codex/state/agent-cycles/{cycle_id}.json`

Minimum fields:

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

## Phases

`agent-cycle` has two phases:

- `review`
- `apply`

The default first call starts `review`.
The approval call resumes `apply` from saved cycle state.

## Review Phase

### 1. Freeze the benchmark prompt

- read the benchmark prompt from the given file
- do not rewrite the prompt during the cycle unless the user explicitly asks
- if the prompt is still vague, stop and ask the user to fix the benchmark first

### 2. Create cycle state

- create a fresh `cycle_id`
- save cycle state with:
  - `benchmark_prompt_path`
  - empty review artifact paths
  - `status = review_running`

### 3. Run `self_improving_agent`

- create a fresh run id
- prefer:

```bash
.venv/bin/python -m agents.self_improving_agent.run --prompt-file <prompt-file> --run-id <run-id>
```

- do not reuse a mixed or hand-edited old run directory
- save `run_id` and `run_dir` into cycle state

### 4. Verify base run artifacts

Check that the run directory contains:

- `input.json`
- `output.json`
- `events.jsonl`
- `meta.json`

If any of these are missing or inconsistent, stop and report that the cycle failed before evaluation.

### 5. Run evaluator sub-agent

Use the evaluator sub-agent defined by `.codex/agents/evaluator/AGENTS.md`.

The evaluator sub-agent must:

- read only:
  - `input.json`
  - `output.json`
  - `events.jsonl`
  - `meta.json`
  - `artifacts/{run_id}/project/`
- write `runs/{run_id}/evaluation.json`

Use this shape:

```json
{
  "summary": "string",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "suggested_changes": ["string"],
  "confidence": 0.0
}
```

Keep the evaluation concrete. Judge the actual answer against the fixed benchmark prompt.
Main Codex should verify that `evaluation.json` now exists and then save its path into cycle state.
Main Codex should also confirm the generated project path under `artifacts/{run_id}/project/` exists.

Do not directly author `evaluation.json` in Main Codex as the default path.
If the evaluator sub-agent cannot run, stop and mark the cycle `failed`.

### 6. Run critic sub-agent

Use the critic sub-agent defined by `.codex/agents/critic/AGENTS.md`.

The critic sub-agent must:

- read:
  - `input.json`
  - `output.json`
  - `events.jsonl`
  - `meta.json`
  - `evaluation.json`
  - `artifacts/{run_id}/project/`
- write `runs/{run_id}/critique.json`

Use this shape:

```json
{
  "verdict": "accept | narrow | reject",
  "summary": "string",
  "approved_changes": ["string"],
  "concerns": ["string"],
  "confidence": 0.0
}
```

The critic must narrow the next step, reject weak claims, and keep the approved change list small.
Main Codex should verify that `critique.json` now exists and then save its path into cycle state.

Do not directly author `critique.json` in Main Codex as the default path.
If the critic sub-agent cannot run, stop and mark the cycle `failed`.

### 7. Diagnose

Combine the run, evaluation, and critique into one short diagnosis that says:

- what failed or felt weak
- what single change is most worth doing next
- whether that change belongs in prompt text, run logic, or artifact schema
- what should stay unchanged

Keep it small and actionable.
Save the diagnosis and the approved candidate change into cycle state.

### 8. Report to the user

Report:

- `cycle_id`
- benchmark prompt source
- run id
- key weakness
- proposed next change
- change area
- whether the cycle is waiting for approval

Then set cycle state to `awaiting_approval`.
This report is the end of the review phase.

## Apply Phase

### 9. Approval gate

- do not edit code before user approval
- on approval, load the saved cycle state by `cycle_id`
- set status to `approved`, then `apply_running`
- if the cycle state is missing or incomplete, stop and report the blocker

### 10. Run `improve-agent`

- use the saved diagnosis and approved change
- make one bounded change only
- keep the JSON and JSONL artifact contract stable unless the diagnosis clearly requires schema work

### 11. Verify improvement

- run the relevant tests
- report what changed
- report what should be run next in the next cycle
- set cycle state to `improved`

Benchmark rerun is not part of the same apply phase by default.
If the user wants a rerun, start the next cycle after this one is closed.

## Stop Rules

- stop if the benchmark prompt is not stable
- stop if the run fails
- stop if evaluator or critic sub-agent execution fails
- stop if `evaluation.json` or `critique.json` cannot be written with confidence
- stop after reporting the diagnosis if the user has not approved the change

## Boundaries

- keep one cycle focused on one benchmark prompt
- keep one approved implementation step bounded
- do not widen scope into tool use, loops, or large refactors unless the user explicitly asks
