---
name: improve-agent
description: Apply one approved change to the simple prompt agent module without widening scope.
argument-hint: "<approved diagnosis or target file>"
---

# improve-agent

Use this when Main Codex already has an approved diagnosis.

## Goal

Make one bounded improvement to `simple_prompt_agent`.

## Default Targets

- `agents/simple_prompt_agent/AGENTS.md`
- `agents/simple_prompt_agent/prompts/system.txt`
- `agents/simple_prompt_agent/run.py`

## Rules

- change only what the diagnosis requires
- keep the JSON and JSONL artifact contract stable unless explicitly told to change it
- do not add loops or tool use unless the user explicitly asks
- keep wording simple
- run the relevant tests after the change
