from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from minimal_agent_harness.engine import build_default_runner


@dataclass
class TaskDefinition:
    name: str
    instruction: str
    expectation: dict[str, Any]
    workspace_dir: Path | None


def load_task(task_dir: Path) -> TaskDefinition:
    instruction = (task_dir / "instruction.md").read_text().strip()
    expectation = json.loads((task_dir / "expected.json").read_text())
    workspace_dir = task_dir / "workspace"
    return TaskDefinition(
        name=task_dir.name,
        instruction=instruction,
        expectation=expectation,
        workspace_dir=workspace_dir if workspace_dir.exists() else None,
    )


def prepare_workspace(task: TaskDefinition, destination: Path) -> Path:
    workspace = destination / task.name / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    if task.workspace_dir is not None:
        shutil.copytree(task.workspace_dir, workspace, dirs_exist_ok=True)
    return workspace


def verify_run(response: str, log_payload: dict[str, Any], expectation: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []

    response_contains = expectation.get("response_contains")
    if response_contains and response_contains not in response:
        failures.append(f"response missing substring: {response_contains}")

    required_event_types = expectation.get("required_event_types", [])
    event_types = [event["type"] for event in log_payload.get("events", [])]
    for event_type in required_event_types:
        if event_type not in event_types:
            failures.append(f"missing event type: {event_type}")

    required_tool_names = expectation.get("required_tool_names", [])
    tool_names = [
        event["tool_name"]
        for event in log_payload.get("events", [])
        if event.get("type") == "tool_call"
    ]
    for tool_name in required_tool_names:
        if tool_name not in tool_names:
            failures.append(f"missing tool call: {tool_name}")

    return (not failures), failures


def run_benchmark(tasks_dir: str | Path, log_root: str | Path = "benchmark_runs") -> dict[str, Any]:
    tasks_path = Path(tasks_dir)
    log_root_path = Path(log_root)
    results: list[dict[str, Any]] = []

    for task_dir in sorted(path for path in tasks_path.iterdir() if path.is_dir()):
        task = load_task(task_dir)
        workspace = prepare_workspace(task, log_root_path)
        log_file = log_root_path / task.name / "run.json"
        runner = build_default_runner(workspace_root=workspace)
        response = runner.run(task.instruction, log_file=str(log_file))
        log_payload = json.loads(log_file.read_text())
        passed, failures = verify_run(response, log_payload, task.expectation)
        results.append(
            {
                "task": task.name,
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "failures": failures,
            }
        )

    passed_count = sum(1 for result in results if result["passed"])
    return {
        "total": len(results),
        "passed": passed_count,
        "avg_score": (passed_count / len(results)) if results else 0.0,
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the tiny deterministic benchmark suite")
    parser.add_argument(
        "--tasks-dir",
        default="benchmarks/tasks",
        help="Path to the benchmark task directory",
    )
    parser.add_argument(
        "--log-root",
        default="benchmark_runs",
        help="Directory for per-task logs and workspaces",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    summary = run_benchmark(tasks_dir=args.tasks_dir, log_root=args.log_root)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
