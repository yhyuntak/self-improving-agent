import json
import subprocess
import sys

from minimal_agent_harness.experiments import run_experiment_comparison


def test_run_experiment_comparison_persists_report(tmp_path):
    baseline_config = tmp_path / "baseline.json"
    variant_config = tmp_path / "variant.json"
    output_path = tmp_path / "report.json"

    baseline_config.write_text(
        json.dumps({"name": "baseline", "backend_name": "scripted"}, indent=2)
    )
    variant_config.write_text(
        json.dumps({"name": "variant", "backend_name": "scripted"}, indent=2)
    )

    report = run_experiment_comparison(
        tasks_dir="benchmarks/tasks",
        baseline_config_path=baseline_config,
        variant_config_path=variant_config,
        output_path=output_path,
        log_root=tmp_path / "runs",
    )

    assert report["winner"] == "tie"
    assert report["baseline"]["summary"]["passed"] == 3
    assert report["variant"]["summary"]["passed"] == 3
    assert output_path.exists()


def test_experiments_cli_runs_and_prints_report(tmp_path):
    baseline_config = tmp_path / "baseline.json"
    variant_config = tmp_path / "variant.json"
    output_path = tmp_path / "report.json"

    baseline_config.write_text(
        json.dumps({"name": "baseline", "backend_name": "scripted"}, indent=2)
    )
    variant_config.write_text(
        json.dumps({"name": "variant", "backend_name": "scripted"}, indent=2)
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "minimal_agent_harness.experiments",
            "--tasks-dir",
            "benchmarks/tasks",
            "--baseline-config",
            str(baseline_config),
            "--variant-config",
            str(variant_config),
            "--output",
            str(output_path),
            "--log-root",
            str(tmp_path / "runs"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    report = json.loads(result.stdout)
    assert report["winner"] == "tie"
    assert report["baseline"]["config"]["name"] == "baseline"
    assert report["variant"]["config"]["name"] == "variant"
