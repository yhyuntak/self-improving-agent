import json
import subprocess
import sys
from pathlib import Path

from minimal_agent_harness.self_improvement import run_self_improvement_loop


def test_self_improvement_promotes_only_better_candidates(tmp_path):
    baseline = tmp_path / "baseline.json"
    better = tmp_path / "better.json"
    worse = tmp_path / "worse.json"
    promoted = tmp_path / "current-best.json"
    summary_path = tmp_path / "summary.json"

    baseline.write_text(json.dumps({"name": "baseline", "backend_name": "scripted"}, indent=2))
    better.write_text(json.dumps({"name": "better", "backend_name": "scripted"}, indent=2))
    worse.write_text(json.dumps({"name": "worse", "backend_name": "scripted"}, indent=2))

    def fake_runner(**kwargs):
        variant_name = json.loads(Path(kwargs["variant_config_path"]).read_text())["name"]
        winner = "variant" if variant_name == "better" else "baseline"
        return {
            "winner": winner,
            "baseline": {"summary": {"passed": 2, "avg_score": 2 / 3}},
            "variant": {"summary": {"passed": 3, "avg_score": 1.0}},
        }

    summary = run_self_improvement_loop(
        tasks_dir="benchmarks/tasks",
        current_best_config_path=baseline,
        candidate_config_paths=[better, worse],
        promoted_config_path=promoted,
        summary_output_path=summary_path,
        log_root=tmp_path / "logs",
        comparison_runner=fake_runner,
    )

    promoted_payload = json.loads(promoted.read_text())
    assert promoted_payload["name"] == "better"
    assert summary["decisions"][0]["promoted"] is True
    assert summary["decisions"][1]["promoted"] is False
    assert summary["decisions"][1]["status"] == "ok"


def test_self_improvement_discards_crashing_candidate(tmp_path):
    baseline = tmp_path / "baseline.json"
    crashing = tmp_path / "crashing.json"
    promoted = tmp_path / "current-best.json"
    summary_path = tmp_path / "summary.json"

    baseline.write_text(json.dumps({"name": "baseline", "backend_name": "scripted"}, indent=2))
    crashing.write_text(json.dumps({"name": "crashing", "backend_name": "scripted"}, indent=2))

    def crashing_runner(**kwargs):
        raise RuntimeError("candidate failed verification")

    summary = run_self_improvement_loop(
        tasks_dir="benchmarks/tasks",
        current_best_config_path=baseline,
        candidate_config_paths=[crashing],
        promoted_config_path=promoted,
        summary_output_path=summary_path,
        log_root=tmp_path / "logs",
        comparison_runner=crashing_runner,
    )

    promoted_payload = json.loads(promoted.read_text())
    assert promoted_payload["name"] == "baseline"
    assert summary["decisions"][0]["promoted"] is False
    assert summary["decisions"][0]["status"] == "crash"
    assert "candidate failed verification" in summary["decisions"][0]["error"]
    crash_report = Path(summary["decisions"][0]["report_path"])
    assert crash_report.exists()


def test_self_improvement_cli_writes_summary_and_promoted_config(tmp_path):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    promoted = tmp_path / "promoted.json"
    summary = tmp_path / "summary.json"

    baseline.write_text(json.dumps({"name": "baseline", "backend_name": "scripted"}, indent=2))
    candidate.write_text(json.dumps({"name": "candidate", "backend_name": "scripted"}, indent=2))

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "minimal_agent_harness.self_improvement",
            "--tasks-dir",
            "benchmarks/tasks",
            "--current-best-config",
            str(baseline),
            "--candidate-config",
            str(candidate),
            "--promoted-config-output",
            str(promoted),
            "--summary-output",
            str(summary),
            "--log-root",
            str(tmp_path / "logs"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["final_best"]["config"]["name"] == "baseline"
    assert promoted.exists()
    assert summary.exists()
