import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agents.simple_prompt_agent.run import build_run_paths, run_once


class FakeClient:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls = []

    def create_response(self, *, model: str, fallback_models: list[str], system_prompt: str, user_prompt: str) -> str:
        self.calls.append(
            {
                "model": model,
                "fallback_models": fallback_models,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        return self.response_text


def test_run_once_writes_expected_json_artifacts(tmp_path):
    client = FakeClient('{"final_answer":"A short answer."}')

    run_paths = run_once(
        "Draft a tiny note-taking app concept.",
        runs_dir=tmp_path,
        run_id="demo-run",
        model="test-model",
        fallback_models=[],
        client=client,
    )

    input_payload = json.loads(run_paths.input_file.read_text())
    output_payload = json.loads(run_paths.output_file.read_text())
    meta_payload = json.loads(run_paths.meta_file.read_text())
    event_lines = [json.loads(line) for line in run_paths.events_file.read_text().splitlines()]

    assert input_payload["prompt"] == "Draft a tiny note-taking app concept."
    assert output_payload["final_answer"] == "A short answer."
    assert meta_payload["agent_id"] == "simple_prompt_agent"
    assert [event["event"] for event in event_lines] == [
        "run_started",
        "user_message",
        "assistant_message",
        "run_finished",
    ]
    assert len(client.calls) == 1


def test_run_once_rejects_invalid_model_json(tmp_path):
    client = FakeClient('{"summary":"missing final answer"}')

    with pytest.raises(ValueError):
        run_once(
            "Draft a tiny note-taking app concept.",
            runs_dir=tmp_path,
            run_id="bad-run",
            model="test-model",
            fallback_models=[],
            client=client,
        )


def test_cli_smoke_run_with_fake_response_env(tmp_path):
    env = os.environ.copy()
    env["SIMPLE_PROMPT_AGENT_FAKE_RESPONSE_JSON"] = '{"final_answer":"CLI smoke answer."}'

    subprocess.run(
        [
            sys.executable,
            "-m",
            "agents.simple_prompt_agent.run",
            "Draft a tiny concept note.",
            "--run-id",
            "cli-smoke",
            "--runs-dir",
            str(tmp_path),
        ],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )

    run_paths = build_run_paths(tmp_path, "cli-smoke")
    assert run_paths.input_file.exists()
    assert run_paths.output_file.exists()
    assert run_paths.events_file.exists()
    assert run_paths.meta_file.exists()


def test_repo_contains_local_subagent_and_skill_scaffolds():
    assert Path(".codex/agents/evaluator/AGENTS.md").exists()
    assert Path(".codex/agents/critic/AGENTS.md").exists()
    assert Path(".codex/skills/diagnose-agent/SKILL.md").exists()
    assert Path(".codex/skills/improve-agent/SKILL.md").exists()
