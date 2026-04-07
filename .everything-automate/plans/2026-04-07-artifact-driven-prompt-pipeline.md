---
status: done
created: 2026-04-07
slug: artifact-driven-prompt-pipeline
---

# Plan: artifact-driven-prompt-pipeline

## Requirements Summary

### Desired Outcome
- Start from a single prompt call, not an agent loop.
- Persist every stage as files on disk rather than shared in-memory state.
- Let an evaluation step read generated artifacts and produce structured diagnosis.
- Keep the first version compact and fun to iterate on.

### In-Scope
- A document-driven run directory contract
- A single-prompt generator that writes output artifacts
- An evaluator step that reads artifacts and writes diagnosis artifacts
- A critic step that reviews the diagnosis and writes approval or pushback
- Simple CLI entrypoints and smoke-testable scripts

### Non-Goals
- Full task-agent loop with tools, memory, retries, and orchestration
- Automatic code modification by the first version
- Promotion, rollback, or self-improvement automation in the first cut
- Large multi-agent decomposition

### Decision Boundaries
- File artifacts are the interface between stages
- Keep the first version human-readable first, machine-readable second
- Prefer `Markdown + sidecar JSON` over pure JSON or pure memory passing
- Reuse the existing Python project structure instead of creating a separate repo

## Quick Context Check

- Task statement: design a simple first-stage system for `single prompt -> artifact output -> evaluation`.
- Known facts:
  - The repo already has OpenRouter-backed model access and CLI entrypoints.
  - The repo already has benchmark and comparison infrastructure, but that is deeper than the requested starting point.
  - The user wants evaluation to read dropped files, not internal memory.
- Constraints:
  - Keep the design compact.
  - Avoid deep agent-loop complexity.
  - Make room for later growth into self-improvement.
- Likely touchpoints:
  - `src/minimal_agent_harness/`
  - `README.md`
  - `tests/`
- Unknowns:
  - Exact product/theme used for the first real run. Not blocking for the first scaffold.

## Problem Summary

The current repo can run benchmarks and compare configs, but it does not yet support the simpler product-first workflow the user wants:

```text
topic
-> one LLM call
-> output file(s)
-> evaluator reads files
-> critic reviews evaluator judgment
-> proposed next changes are written as artifacts
```

The first useful milestone is not autonomous improvement. It is a clean artifact contract plus the first two analysis stages.

## What Matters Most

- Keep the first version small enough to understand in one sitting.
- Make artifacts stable enough that later stages can evolve independently.
- Avoid overcommitting to a deep agent architecture too early.

## Options Considered

### Option A: Extend the current benchmark/self-improvement path directly
- Pros:
  - Reuses existing machinery.
- Cons:
  - Too deep for the current goal.
  - Keeps the work benchmark-shaped instead of product-shaped.

### Option B: Build a file-based prompt/evaluate/critic pipeline first
- Pros:
  - Matches the user's desired mental model.
  - Easy to inspect and debug.
  - Leaves room for later implementer or installer stages.
- Cons:
  - Initial scoring may be qualitative rather than benchmark-like.

### Option C: Build the full multi-agent loop immediately
- Pros:
  - Closer to the long-term vision.
- Cons:
  - Too much scope too early.
  - Harder to debug and reason about failure sources.

## Recommended Direction

Choose **Option B**.

Build a **document-driven prompt pipeline** with three stages only:

1. `generator`
2. `evaluator`
3. `critic`

The generator writes the initial output.  
The evaluator reads artifacts and writes diagnosis.  
The critic reads the diagnosis and writes a constrained judgment about whether the diagnosis is solid and what class of change is justified next.

Do **not** implement automatic fixing yet. Instead, end the first version with a machine-readable recommendation artifact.

## Proposed Artifact Contract

Each run gets a dedicated directory:

```text
artifacts/runs/{run_id}/
  topic.md
  generator/
    output.md
    meta.json
  evaluator/
    diagnosis.json
    notes.md
  critic/
    review.json
    notes.md
```

Minimum semantics:

- `topic.md`
  - user topic or product prompt
- `generator/output.md`
  - the LLM-produced artifact
- `generator/meta.json`
  - model, backend, prompt path, timestamps
- `evaluator/diagnosis.json`
  - observed weaknesses, missing capabilities, suggested next changes, confidence
- `critic/review.json`
  - whether the diagnosis is accepted, narrowed, or rejected

## Acceptance Criteria

- [x] AC-1: Define a stable artifact contract and run-directory layout.
  - TC: A single documented run layout exists and is used consistently by scripts.
  - TC: The repo has one clear place where run artifacts are written.

- [x] AC-2: Add a single-prompt generator script that writes output artifacts to disk.
  - TC: Given a topic, the generator writes `topic.md`, `generator/output.md`, and `generator/meta.json`.
  - TC: The generator can run with the existing OpenRouter-backed model setup.

- [x] AC-3: Add an evaluator script that reads generator artifacts and writes diagnosis artifacts.
  - TC: The evaluator reads only file artifacts from a run directory.
  - TC: The evaluator writes `evaluator/diagnosis.json` and `evaluator/notes.md`.

- [x] AC-4: Add a critic script that reviews the diagnosis and writes a constrained judgment artifact.
  - TC: The critic can mark the diagnosis as `accept`, `narrow`, or `reject`.
  - TC: The critic writes `critic/review.json` and `critic/notes.md`.

- [x] AC-5: Add lightweight tests and one smoke flow for the end-to-end document pipeline.
  - TC: Tests validate artifact creation and stage contracts without requiring a real OpenRouter live call.
  - TC: A local smoke command can run generator -> evaluator -> critic on one sample topic.

## Verification Steps

- Run unit tests for artifact path creation and stage contracts.
- Run one smoke command that creates a full run directory from `topic.md` through `critic/review.json`.
- Inspect one sample run directory manually to confirm that every stage reads files rather than in-memory outputs.

## Implementation Order

1. Add the run-directory artifact contract and helper utilities.
2. Add the generator CLI and artifact writer.
3. Add the evaluator CLI that consumes generator artifacts.
4. Add the critic CLI that consumes evaluator artifacts.
5. Add tests and one documented smoke flow.

## Risks And Mitigations

- Risk: The evaluator or critic becomes too open-ended and hard to verify.
  - Mitigation: Force structured JSON outputs with a narrow schema.

- Risk: The first version drifts back toward a hidden in-memory agent chain.
  - Mitigation: Require every stage to read from the previous stage's files.

- Risk: The first version becomes too deep too early.
  - Mitigation: Exclude implementer, installer, promotion, and rollback from this plan.

## Handoff

```yaml
task_id: artifact-driven-prompt-pipeline
plan_path: .everything-automate/plans/2026-04-07-artifact-driven-prompt-pipeline.md
approval_state: approved
execution_unit: small
recommended_mode: direct
recommended_agents:
  - none_required_initially
verification_lane: local_tests_plus_one_smoke_flow
open_risks:
  - evaluator schema may still need one revision after the first smoke run
  - the first sample topic may bias the artifact contract if chosen too narrowly
```
