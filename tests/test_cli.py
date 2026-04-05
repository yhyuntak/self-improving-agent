import json
import subprocess
import sys


def test_cli_runs_and_emits_log(tmp_path):
    log_file = tmp_path / "cli-run.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "minimal_agent_harness.cli",
            "inspect the sample task",
            "--log-file",
            str(log_file),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Completed sample run" in result.stdout

    payload = json.loads(log_file.read_text())
    assert payload["events"][-1]["type"] == "finish"
