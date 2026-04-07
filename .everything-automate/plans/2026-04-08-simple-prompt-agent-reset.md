# Simple Prompt Agent Reset

This plan was approved and executed.

## Task Summary

Reset the repo around one real CLI agent module called `simple_prompt_agent`.

## Desired Outcome

- one real agent module
- JSON and JSONL run artifacts
- local evaluator and critic agent scaffolds
- local diagnose and improve skill scaffolds
- docs and tests for the new flow

## In Scope

- new `agents/simple_prompt_agent/`
- new run artifact contract
- new `.codex/agents`
- new `.codex/skills`
- new docs and tests

## Non-Goals

- no loop
- no tool use
- no benchmark suite
- no self-improvement automation

## Design Direction

Main Codex orchestrates.
`simple_prompt_agent` runs headlessly.
Evaluator and critic read files from disk.

## Test Strategy

Mixed:

- unit checks for artifact writing
- CLI smoke test
- scaffold existence checks

## Execute Handoff

- `task_id`: `simple-prompt-agent-reset`
- `plan_path`: `/home/yhyuntak/workspace/self-improving-agent/.everything-automate/plans/2026-04-08-simple-prompt-agent-reset.md`
- `approval_state`: `approved`
- `execution_unit`: `AC`
- `test_strategy`: `mixed`
- `open_risks`:
  - `future artifact contract drift`
  - `future scope creep back into harness language`
