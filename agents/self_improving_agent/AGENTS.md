# Self Improving Agent

This module is the main project-building agent in the repo.

It does one thing:

- take one user prompt
- call one model once
- turn the model output into real project files
- write run artifacts to disk

It does not have a loop yet.
It does not use tools yet.

The output contract matters more than the internal logic.

Stable run-history files:

- `input.json`
- `output.json`
- `events.jsonl`
- `meta.json`

Generated project output lives here:

- `artifacts/{run_id}/project/`

Later changes may improve the module, but they should keep the output directory contract stable unless Main Codex explicitly decides to change it.
