import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import agents.self_improving_agent.run as run_module
from agents.self_improving_agent.run import (
    build_run_paths,
    default_model,
    default_request_timeout_seconds,
    load_prompt_from_args,
    run_once,
)


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


class RaisingClient:
    def __init__(self, exc: Exception):
        self.exc = exc
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
        raise self.exc


def test_run_once_writes_history_and_project_artifacts(tmp_path):
    client = FakeClient(
        json.dumps(
            {
                "summary": "Created a tiny todo app scaffold.",
                "files": [
                    {"path": "package.json", "content": "{\n  \"name\": \"todo-app\"\n}\n"},
                    {"path": "src/main.js", "content": "console.log('todo');\n"},
                ],
                "start_command": "npm run dev",
                "test_command": "npm test",
                "e2e_command": "",
            }
        )
    )

    run_paths = run_once(
        "Build a tiny todo app.",
        runs_dir=tmp_path / "runs",
        artifacts_dir=tmp_path / "artifacts",
        run_id="demo-run",
        model="test-model",
        fallback_models=[],
        client=client,
    )

    input_payload = json.loads(run_paths.input_file.read_text())
    output_payload = json.loads(run_paths.output_file.read_text())
    meta_payload = json.loads(run_paths.meta_file.read_text())
    event_lines = [json.loads(line) for line in run_paths.events_file.read_text().splitlines()]

    assert input_payload["agent_id"] == "self_improving_agent"
    assert output_payload["project_dir"] == str(run_paths.project_root)
    assert output_payload["created_files"] == ["package.json", "src/main.js"]
    assert meta_payload["artifact_project_dir"] == str(run_paths.project_root)
    assert (run_paths.project_root / "package.json").exists()
    assert (run_paths.project_root / "src/main.js").exists()
    assert [event["event"] for event in event_lines] == [
        "run_started",
        "user_message",
        "assistant_message",
        "run_finished",
    ]
    assert len(client.calls) == 1


def test_run_once_rejects_invalid_file_path(tmp_path):
    client = FakeClient(
        json.dumps(
            {
                "summary": "bad",
                "files": [{"path": "../escape.txt", "content": "x"}],
                "start_command": "",
                "test_command": "",
                "e2e_command": "",
            }
        )
    )

    with pytest.raises(ValueError):
        run_once(
            "Build a tiny todo app.",
            runs_dir=tmp_path / "runs",
            artifacts_dir=tmp_path / "artifacts",
            run_id="bad-run",
            model="test-model",
            fallback_models=[],
            client=client,
        )


def test_run_once_replaces_full_run_state_for_reused_run_id(tmp_path):
    first_client = FakeClient(
        json.dumps(
            {
                "summary": "first",
                "files": [{"path": "old.txt", "content": "old\n"}],
                "start_command": "",
                "test_command": "",
                "e2e_command": "",
            }
        )
    )
    second_client = FakeClient(
        json.dumps(
            {
                "summary": "second",
                "files": [{"path": "new.txt", "content": "new\n"}],
                "start_command": "",
                "test_command": "",
                "e2e_command": "",
            }
        )
    )

    first_run = run_once(
        "Build a tiny todo app.",
        runs_dir=tmp_path / "runs",
        artifacts_dir=tmp_path / "artifacts",
        run_id="same-run",
        model="test-model",
        fallback_models=[],
        client=first_client,
    )
    first_run.run_root.joinpath("evaluation.json").write_text('{"summary":"old eval"}\n', encoding="utf-8")
    first_run.run_root.joinpath("critique.json").write_text('{"verdict":"reject"}\n', encoding="utf-8")
    first_run.run_root.joinpath("stale.txt").write_text("stale\n", encoding="utf-8")
    first_run.artifacts_root.joinpath("stale-artifact.txt").write_text("stale\n", encoding="utf-8")

    run_paths = run_once(
        "Build a tiny todo app again.",
        runs_dir=tmp_path / "runs",
        artifacts_dir=tmp_path / "artifacts",
        run_id="same-run",
        model="test-model",
        fallback_models=[],
        client=second_client,
    )

    output_payload = json.loads(run_paths.output_file.read_text())
    event_lines = [json.loads(line) for line in run_paths.events_file.read_text().splitlines()]
    assert output_payload["created_files"] == ["new.txt"]
    assert not (run_paths.project_root / "old.txt").exists()
    assert (run_paths.project_root / "new.txt").exists()
    assert [event["event"] for event in event_lines] == [
        "run_started",
        "user_message",
        "assistant_message",
        "run_finished",
    ]
    assert event_lines[1]["content"] == "Build a tiny todo app again."
    assert all(event.get("content") != "Build a tiny todo app." for event in event_lines)
    assert not run_paths.run_root.joinpath("evaluation.json").exists()
    assert not run_paths.run_root.joinpath("critique.json").exists()
    assert not run_paths.run_root.joinpath("stale.txt").exists()
    assert not run_paths.artifacts_root.joinpath("stale-artifact.txt").exists()


def test_run_once_writes_failure_artifacts_when_client_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(run_module, "default_request_timeout_seconds", lambda: 12.5)
    client = RaisingClient(TimeoutError("model request timed out"))

    with pytest.raises(TimeoutError):
        run_once(
            "Build a tiny todo app.",
            runs_dir=tmp_path / "runs",
            artifacts_dir=tmp_path / "artifacts",
            run_id="timeout-run",
            model="test-model",
            fallback_models=[],
            client=client,
        )

    run_paths = build_run_paths(tmp_path / "runs", tmp_path / "artifacts", "timeout-run")
    meta_payload = json.loads(run_paths.meta_file.read_text())
    event_lines = [json.loads(line) for line in run_paths.events_file.read_text().splitlines()]

    assert not run_paths.output_file.exists()
    assert meta_payload["status"] == "error"
    assert meta_payload["request_timeout_seconds"] == 12.5
    assert meta_payload["error_type"] == "TimeoutError"
    assert meta_payload["error_message"] == "model request timed out"
    assert [event["event"] for event in event_lines] == [
        "run_started",
        "user_message",
        "run_failed",
        "run_finished",
    ]
    assert event_lines[2]["error_type"] == "TimeoutError"
    assert event_lines[2]["error_message"] == "model request timed out"
    assert event_lines[3]["status"] == "error"


def test_cli_smoke_run_with_fake_response_env(tmp_path):
    env = os.environ.copy()
    env["SELF_IMPROVING_AGENT_FAKE_RESPONSE_JSON"] = json.dumps(
        {
            "summary": "Created app files.",
            "files": [{"path": "README.md", "content": "# app\n"}],
            "start_command": "npm run dev",
            "test_command": "npm test",
            "e2e_command": "npm run e2e",
        }
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "agents.self_improving_agent.run",
            "Build a tiny app.",
            "--run-id",
            "cli-smoke",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )

    run_paths = build_run_paths(tmp_path / "runs", tmp_path / "artifacts", "cli-smoke")
    assert run_paths.input_file.exists()
    assert run_paths.output_file.exists()
    assert run_paths.events_file.exists()
    assert run_paths.meta_file.exists()
    assert (run_paths.project_root / "README.md").exists()


def test_cli_supports_prompt_file(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Build a todo app.\n\nKeep the scope small.\n", encoding="utf-8")

    env = os.environ.copy()
    env["SELF_IMPROVING_AGENT_FAKE_RESPONSE_JSON"] = json.dumps(
        {
            "summary": "Created prompt-file app.",
            "files": [{"path": "README.md", "content": "# prompt file\n"}],
            "start_command": "",
            "test_command": "",
            "e2e_command": "",
        }
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "agents.self_improving_agent.run",
            "--prompt-file",
            str(prompt_file),
            "--run-id",
            "file-smoke",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )

    run_paths = build_run_paths(tmp_path / "runs", tmp_path / "artifacts", "file-smoke")
    input_payload = json.loads(run_paths.input_file.read_text())
    assert input_payload["prompt"] == "Build a todo app.\n\nKeep the scope small."


def test_load_prompt_from_args_rejects_invalid_combinations(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Build a todo app.", encoding="utf-8")

    with pytest.raises(ValueError):
        load_prompt_from_args("inline prompt", str(prompt_file))

    with pytest.raises(ValueError):
        load_prompt_from_args(None, None)


def test_default_model_prefers_gemma_when_env_is_unset(monkeypatch):
    monkeypatch.setattr(run_module, "load_dotenv_if_present", lambda: None)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    assert default_model() == "google/gemma-4-31b-it"


def test_default_request_timeout_seconds_has_default_and_env_override(monkeypatch):
    monkeypatch.setattr(run_module, "load_dotenv_if_present", lambda: None)
    monkeypatch.delenv("OPENROUTER_TIMEOUT_SECONDS", raising=False)
    assert default_request_timeout_seconds() == 30.0

    monkeypatch.setenv("OPENROUTER_TIMEOUT_SECONDS", "12.5")
    assert default_request_timeout_seconds() == 12.5


def test_agent_cycle_skill_mentions_project_artifacts_for_evaluator_and_critic():
    skill_text = Path(".codex/skills/agent-cycle/SKILL.md").read_text(encoding="utf-8")
    evaluator_section = skill_text.split("### 5. Run evaluator sub-agent", 1)[1].split("### 6. Run critic sub-agent", 1)[0]
    critic_section = skill_text.split("### 6. Run critic sub-agent", 1)[1].split("### 7. Diagnose", 1)[0]

    assert "artifacts/{run_id}/project/" in evaluator_section
    assert "artifacts/{run_id}/project/" in critic_section
