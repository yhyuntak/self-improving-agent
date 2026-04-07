# Simple Prompt Agent

This module is the first real agent module in the repo.

It does one thing:

- take one user prompt
- call one model once
- return one JSON answer
- write run artifacts to disk

It does not have a loop yet.
It does not use tools yet.

The output contract matters more than the internal logic.

Stable output files:

- `input.json`
- `output.json`
- `events.jsonl`
- `meta.json`

Later changes may improve the module, but they should keep the file contract stable unless Main Codex explicitly decides to change it.
