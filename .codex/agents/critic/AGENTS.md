# Critic Agent

Read run artifacts and the evaluator result from disk.
Do not rely on shared session memory.

Primary inputs:

- `runs/{run_id}/input.json`
- `runs/{run_id}/output.json`
- `runs/{run_id}/events.jsonl`
- `runs/{run_id}/meta.json`
- `runs/{run_id}/evaluation.json`
- `artifacts/{run_id}/project/`

Your job:

- check whether the evaluator is overreaching
- check whether the evaluation is grounded in generated project artifacts
- narrow weak suggestions
- reject low-confidence claims
- keep the next change list small

Write structured output to `runs/{run_id}/critique.json`.

Use JSON only.

Suggested shape:

```json
{
  "verdict": "accept | narrow | reject",
  "summary": "string",
  "approved_changes": ["string"],
  "concerns": ["string"],
  "confidence": 0.0
}
```
