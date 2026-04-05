import json
import subprocess
import sys

from minimal_agent_harness.benchmark import run_benchmark


def test_benchmark_runner_scores_all_tasks(tmp_path):
    summary = run_benchmark("benchmarks/tasks", log_root=tmp_path)

    assert summary["total"] == 3
    assert summary["passed"] == 3
    assert summary["avg_score"] == 1.0
    assert all(result["score"] == 1.0 for result in summary["results"])


def test_benchmark_cli_runs_all_tasks(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "minimal_agent_harness.benchmark",
            "--tasks-dir",
            "benchmarks/tasks",
            "--log-root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    summary = json.loads(result.stdout)
    assert summary["total"] == 3
    assert summary["passed"] == 3
