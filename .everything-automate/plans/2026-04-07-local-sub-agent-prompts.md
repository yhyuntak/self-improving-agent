# Local Sub-Agent Prompt Assets

## Requirements Summary

- Keep the current artifact-driven pipeline shape.
- Make `generator`, `evaluator`, and `critic` local sub-agent definitions in a simple form.
- Do not build a new agent loop or a generic agent framework.
- Keep orchestration in Python.
- Keep stage outputs file-based so later stages read artifacts from disk, not shared memory.

## Desired Outcome

The repo should have three local prompt assets for `generator`, `evaluator`, and `critic`, and the Python pipeline should load those assets at runtime. Stage order, artifact paths, JSON parsing, and file writes should stay in code.

## Problem Summary

Right now stage behavior lives inline in `prompt_pipeline.py`. That makes the artifact pipeline work, but it does not yet match the intended shape of "local sub-agents with simple prompts." The next step is to move stage instructions out of inline Python strings and into local prompt assets without adding a second orchestration layer or changing the current artifact contract.

## Why Now

- It makes the role prompts visible and editable as first-class local assets.
- It keeps the system small while moving one step closer to sub-agent orchestration.
- It avoids overcommitting to loops, tools, or a heavier agent runtime too early.

## Success Definition

- `generator`, `evaluator`, and `critic` each have a local prompt asset.
- The existing pipeline still runs in the same fixed order.
- The same artifact tree is produced under `artifacts/runs/{run_id}/`.
- Evaluator and critic still return valid JSON that Python validates and writes to disk.
- Prompt changes can alter stage behavior without changing Python source.

## In Scope

- Add package-local prompt asset files for `generator`, `evaluator`, and `critic`.
- Add one small loader layer for stage prompt assets.
- Refactor `prompt_pipeline.py` to load and render those assets.
- Keep current explicit stage functions:
  - `run_generator`
  - `run_evaluator`
  - `run_critic`
- Add metadata fields needed to track which prompt asset was used.
- Add tests for prompt loading, metadata capture, and failure cases.
- Update docs for the new prompt-asset layout.

## Non-Goals

- No dynamic stage registry.
- No autonomous multi-step agent loop.
- No tool use inside these local sub-agents.
- No prompt marketplace or remote prompt source.
- No changes to `experiments.py` or `self_improvement.py`.
- No benchmark schema changes in this pass.
- No runtime model routing per stage beyond the current global env/config path unless already needed for compatibility.

## Decision Boundaries

- Prompts move out of code; orchestration stays in code.
- Artifact paths and JSON schema stay in Python, not in prompt assets.
- Stage order stays fixed: `generator -> evaluator -> critic`.
- Prompt assets are local files inside the Python package, not repo-root loose files.
- The term "local sub-agent" means file-backed prompt definitions in this pass, not a new standalone execution runtime.

## What Matters Most

- Keep the system compact.
- Preserve the current artifact contract.
- Make prompt edits easy and local.
- Avoid hidden prompt/schema drift.
- Keep later migration to Codex sub-agent orchestration possible.

## Options Considered

### Option A: Keep prompts inline in Python

- Pros:
  - Smallest code surface.
  - No packaging changes.
- Cons:
  - Does not create real local sub-agent assets.
  - Harder to inspect and evolve stage prompts.

### Option B: Package-local prompt assets with a thin loader

- Pros:
  - Matches the intended local sub-agent shape.
  - Keeps orchestration simple.
  - Easy to test and reason about.
- Cons:
  - Needs package data handling.
  - Needs care to prevent prompt/schema drift.

### Option C: Dynamic stage/plugin framework

- Pros:
  - More flexible later.
- Cons:
  - Too heavy for three fixed stages.
  - Blurs ownership between prompts and orchestration.

## Recommended Direction

Choose **Option B**.

Use package-local prompt assets and one tiny loader layer. Keep the current three stage functions and keep all schema validation, artifact paths, and writes in Python. This gives the repo local sub-agent definitions without introducing a new loop or framework.

## Proposed Shape

```text
src/minimal_agent_harness/
  prompt_pipeline.py
  stage_prompts.py
  prompts/
    generator.md
    evaluator.md
    critic.md
```

### Prompt Asset Contract v1

Each stage asset is a plain text template file with:

- `stage`: implied by file name
- `prompt_template`: full prompt body with placeholders
- optional examples embedded in the text

No inheritance, no nested agents, no dynamic routing, no tool calls, and no cross-agent memory in this pass.

### Stage Input Contract

- `generator` reads:
  - topic text
- `evaluator` reads:
  - topic text
  - generator output
- `critic` reads:
  - topic text
  - generator output
  - evaluator diagnosis JSON

## Acceptance Criteria

### AC-1: Local Prompt Assets Exist

- `generator`, `evaluator`, and `critic` prompt assets exist under the package.
- Their paths are loaded through one shared loader module.
- No stage prompt body remains inline in `prompt_pipeline.py`.

### AC-2: Pipeline Keeps Current Contract

- `run_generator`, `run_evaluator`, and `run_critic` still exist as explicit functions.
- The pipeline still writes:
  - `topic.md`
  - `generator/output.md`
  - `generator/meta.json`
  - `evaluator/diagnosis.json`
  - `evaluator/notes.md`
  - `critic/review.json`
  - `critic/notes.md`

### AC-3: Metadata Captures Prompt Identity

- Each stage writes or updates metadata that includes:
  - stage name
  - model
  - fallback models
  - prompt asset path or id
  - prompt content hash
  - created timestamp

### AC-4: Validation Stays Hard in Python

- Evaluator output must parse into the expected JSON shape.
- Critic output must parse into the expected JSON shape.
- Critic verdict must be one of:
  - `accept`
  - `narrow`
  - `reject`
- Invalid or malformed output fails clearly.

### AC-5: Tests Cover Asset Loading and Drift Risks

- Tests verify prompt assets load correctly.
- Tests verify missing prompt asset failure path.
- Tests verify artifact paths remain unchanged.
- Tests verify metadata capture includes prompt identity.
- Tests verify invalid JSON or invalid verdict fails clearly.

## Verification Steps

- Run unit tests for prompt pipeline and asset loading.
- Run one end-to-end smoke flow with fake stage client.
- Confirm the artifact tree matches the current layout.
- Confirm a prompt asset edit changes prompt text sent to the client without Python source edits.
- Confirm install-time packaging includes prompt assets.

## Implementation Order

1. Add prompt asset directory under the package.
2. Add `stage_prompts.py` loader using package resources.
3. Extract current inline stage prompts into asset files.
4. Refactor `prompt_pipeline.py` to render prompt assets.
5. Extend stage metadata with prompt identity and hash.
6. Add tests for loading, metadata, and failure modes.
7. Update docs.

## Risks And How To Reduce Them

- Prompt/schema drift:
  - Keep output schema and verdict validation in Python.
- Package data missing after install:
  - Add explicit package data config and one test for asset loading.
- Scope creep into framework work:
  - Keep only one loader module and fixed stage functions.
- Mixed prompt versions across runs:
  - Record prompt asset identity and hash in metadata.
- Silent failures from malformed model output:
  - Fail hard on invalid JSON shape and invalid verdict.

## Final Handoff

- `task_id`: `local-sub-agent-prompt-assets`
- `plan_path`: `/home/yhyuntak/workspace/self-improving-agent/.everything-automate/plans/2026-04-07-local-sub-agent-prompts.md`
- `approval_state`: `pending`
- `execution_unit`: `single repo refactor`
- `recommended_mode`: `$execute`
- `recommended_agents`: `main Codex only`
- `verification_lane`: `unit tests + fake-client smoke flow`
- `open_risks`:
  - `prompt/schema drift`
  - `package asset loading`
  - `scope creep into a generic framework`
