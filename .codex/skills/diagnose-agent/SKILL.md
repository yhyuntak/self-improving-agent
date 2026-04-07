---
name: diagnose-agent
description: Read one agent run plus evaluation and critique files, then produce a final diagnosis for what should change next.
argument-hint: "<run_id or run directory>"
---

# diagnose-agent

Use this after Main Codex has:

- run `simple_prompt_agent`
- collected `evaluation.json`
- collected `critique.json`

## Goal

Turn one run and its reviews into one final diagnosis.

## Read From Disk

- `input.json`
- `output.json`
- `events.jsonl`
- `meta.json`
- `evaluation.json`
- `critique.json`

## Output

Produce one final diagnosis in simple English with:

- what failed or felt weak
- what change is most worth doing next
- whether that change belongs in:
  - prompt text
  - run logic
  - artifact schema
- what should stay unchanged

Keep the diagnosis small and actionable.
