from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from openai import OpenAI

from agents.self_improving_agent.config import load_dotenv_if_present


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    run_root: Path
    input_file: Path
    output_file: Path
    events_file: Path
    meta_file: Path
    artifacts_root: Path
    project_root: Path


@dataclass(frozen=True)
class GeneratedFile:
    path: str
    content: str


@dataclass(frozen=True)
class AgentOutput:
    summary: str
    files: list[GeneratedFile]
    start_command: str
    test_command: str
    e2e_command: str


class ModelClient(Protocol):
    def create_response(
        self,
        *,
        model: str,
        fallback_models: list[str],
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        ...


class OpenRouterClient:
    def __init__(self) -> None:
        load_dotenv_if_present()
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required")

        self._client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        self._extra_headers = {
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "self-improving-agent"),
        }
        self._timeout_seconds = default_request_timeout_seconds()

    def create_response(
        self,
        *,
        model: str,
        fallback_models: list[str],
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        fake_response = os.getenv("SELF_IMPROVING_AGENT_FAKE_RESPONSE_JSON")
        if fake_response:
            return fake_response

        candidates = [model, *fallback_models]
        last_error: Exception | None = None

        for candidate in candidates:
            try:
                response = self._client.chat.completions.create(
                    model=candidate,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    extra_headers=self._extra_headers,
                    timeout=self._timeout_seconds,
                )
                message = response.choices[0].message.content
                if not message:
                    raise ValueError(f"Model {candidate} returned empty content")
                return message
            except Exception as exc:  # pragma: no cover - live network path
                last_error = exc

        if last_error is None:
            raise RuntimeError("No model candidates were available")
        raise RuntimeError(f"All model candidates failed: {last_error}") from last_error


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_id(prefix: str = "run") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{prefix}-{timestamp}"


def build_run_paths(
    runs_dir: str | Path = "runs",
    artifacts_dir: str | Path = "artifacts",
    run_id: str | None = None,
) -> RunPaths:
    resolved_run_id = run_id or default_run_id()
    run_root = Path(runs_dir) / resolved_run_id
    artifacts_root = Path(artifacts_dir) / resolved_run_id
    project_root = artifacts_root / "project"
    return RunPaths(
        run_id=resolved_run_id,
        run_root=run_root,
        input_file=run_root / "input.json",
        output_file=run_root / "output.json",
        events_file=run_root / "events.jsonl",
        meta_file=run_root / "meta.json",
        artifacts_root=artifacts_root,
        project_root=project_root,
    )


def load_system_prompt() -> tuple[str, str]:
    prompt_path = Path(__file__).with_name("prompts") / "system.txt"
    prompt_text = prompt_path.read_text(encoding="utf-8").strip() + "\n"
    return prompt_text, sha256(prompt_text.encode("utf-8")).hexdigest()


def default_model() -> str:
    load_dotenv_if_present()
    return os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it")


def default_fallback_models() -> list[str]:
    load_dotenv_if_present()
    raw = os.getenv("OPENROUTER_FALLBACK_MODELS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def default_request_timeout_seconds() -> float:
    load_dotenv_if_present()
    raw = os.getenv("OPENROUTER_TIMEOUT_SECONDS", "30")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("OPENROUTER_TIMEOUT_SECONDS must be a positive number") from exc
    if value <= 0:
        raise ValueError("OPENROUTER_TIMEOUT_SECONDS must be a positive number")
    return value


def extract_json_object(text: str) -> dict[str, object]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Model response did not contain a JSON object")
    return json.loads(text[start : end + 1])


def normalize_command(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("command fields must be strings")
    return value.strip()


def normalize_file_path(raw_path: object) -> str:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("file path must be a non-empty string")
    path = Path(raw_path.strip())
    if path.is_absolute():
        raise ValueError("file path must be relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("file path must stay inside the project root")
    return path.as_posix()


def parse_output(text: str) -> AgentOutput:
    payload = extract_json_object(text)
    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("summary must be a non-empty string")

    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("files must be a non-empty list")

    files: list[GeneratedFile] = []
    for item in raw_files:
        if not isinstance(item, dict):
            raise ValueError("each file entry must be an object")
        path = normalize_file_path(item.get("path"))
        content = item.get("content")
        if not isinstance(content, str):
            raise ValueError("file content must be a string")
        files.append(GeneratedFile(path=path, content=content))

    return AgentOutput(
        summary=summary.strip(),
        files=files,
        start_command=normalize_command(payload.get("start_command")),
        test_command=normalize_command(payload.get("test_command")),
        e2e_command=normalize_command(payload.get("e2e_command")),
    )


def append_event(path: Path, event_type: str, **payload: object) -> None:
    event = {"event": event_type, "timestamp": utc_now(), **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def materialize_project_files(project_root: Path, files: list[GeneratedFile]) -> list[str]:
    project_root.mkdir(parents=True, exist_ok=True)
    created_paths: list[str] = []
    for generated in files:
        target = project_root / generated.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(generated.content, encoding="utf-8")
        created_paths.append(generated.path)
    return created_paths


def reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def reset_run_state(run_root: Path, artifacts_root: Path) -> None:
    reset_directory(run_root)
    reset_directory(artifacts_root)


def write_meta(
    path: Path,
    *,
    run_id: str,
    model: str,
    fallback_models: list[str],
    prompt_sha256: str,
    project_root: Path,
    started_at: str,
    request_timeout_seconds: float,
    status: str,
    finished_at: str,
    error_type: str = "",
    error_message: str = "",
) -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "agent_id": "self_improving_agent",
                "model": model,
                "fallback_models": fallback_models,
                "system_prompt_path": "agents/self_improving_agent/prompts/system.txt",
                "system_prompt_sha256": prompt_sha256,
                "artifact_project_dir": str(project_root),
                "request_timeout_seconds": request_timeout_seconds,
                "started_at": started_at,
                "finished_at": finished_at,
                "status": status,
                "error_type": error_type,
                "error_message": error_message,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_prompt_from_args(prompt: str | None, prompt_file: str | None) -> str:
    if prompt and prompt_file:
        raise ValueError("provide either prompt or --prompt-file, not both")
    if prompt_file:
        file_prompt = Path(prompt_file).read_text(encoding="utf-8").strip()
        if not file_prompt:
            raise ValueError("prompt file must not be empty")
        return file_prompt
    if prompt and prompt.strip():
        return prompt
    raise ValueError("prompt or --prompt-file is required")


def run_once(
    prompt: str,
    *,
    runs_dir: str | Path = "runs",
    artifacts_dir: str | Path = "artifacts",
    run_id: str | None = None,
    model: str | None = None,
    fallback_models: list[str] | None = None,
    client: ModelClient | None = None,
) -> RunPaths:
    if not prompt.strip():
        raise ValueError("prompt must not be empty")

    run_paths = build_run_paths(runs_dir=runs_dir, artifacts_dir=artifacts_dir, run_id=run_id)
    reset_run_state(run_paths.run_root, run_paths.artifacts_root)

    started_at = utc_now()
    resolved_model = model or default_model()
    resolved_fallbacks = fallback_models if fallback_models is not None else default_fallback_models()
    resolved_client = client or OpenRouterClient()
    system_prompt, prompt_sha256 = load_system_prompt()
    request_timeout_seconds = default_request_timeout_seconds()

    run_paths.input_file.write_text(
        json.dumps(
            {
                "run_id": run_paths.run_id,
                "agent_id": "self_improving_agent",
                "prompt": prompt,
                "artifact_project_dir": str(run_paths.project_root),
                "created_at": started_at,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    append_event(run_paths.events_file, "run_started", run_id=run_paths.run_id, agent_id="self_improving_agent")
    append_event(run_paths.events_file, "user_message", role="user", content=prompt)

    try:
        raw_response = resolved_client.create_response(
            model=resolved_model,
            fallback_models=resolved_fallbacks,
            system_prompt=system_prompt,
            user_prompt=prompt,
        )
        output = parse_output(raw_response)
        created_files = materialize_project_files(run_paths.project_root, output.files)

        run_paths.output_file.write_text(
            json.dumps(
                {
                    "summary": output.summary,
                    "project_dir": str(run_paths.project_root),
                    "created_files": created_files,
                    "start_command": output.start_command,
                    "test_command": output.test_command,
                    "e2e_command": output.e2e_command,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        append_event(run_paths.events_file, "assistant_message", role="assistant", content=output.summary)
        append_event(run_paths.events_file, "run_finished", status="ok")
        write_meta(
            run_paths.meta_file,
            run_id=run_paths.run_id,
            model=resolved_model,
            fallback_models=resolved_fallbacks,
            prompt_sha256=prompt_sha256,
            project_root=run_paths.project_root,
            started_at=started_at,
            request_timeout_seconds=request_timeout_seconds,
            status="ok",
            finished_at=utc_now(),
        )
        return run_paths
    except Exception as exc:
        append_event(
            run_paths.events_file,
            "run_failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        append_event(run_paths.events_file, "run_finished", status="error")
        write_meta(
            run_paths.meta_file,
            run_id=run_paths.run_id,
            model=resolved_model,
            fallback_models=resolved_fallbacks,
            prompt_sha256=prompt_sha256,
            project_root=run_paths.project_root,
            started_at=started_at,
            request_timeout_seconds=request_timeout_seconds,
            status="error",
            finished_at=utc_now(),
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the self improving agent once")
    parser.add_argument("prompt", nargs="?", help="Prompt to send to the agent")
    parser.add_argument("--prompt-file", default=None, help="Optional file that contains the full prompt")
    parser.add_argument("--run-id", default=None, help="Optional run identifier")
    parser.add_argument("--runs-dir", default="runs", help="Directory for run-history artifacts")
    parser.add_argument("--artifacts-dir", default="artifacts", help="Directory for generated project artifacts")
    parser.add_argument("--model", default=None, help="Optional model override")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    prompt = load_prompt_from_args(args.prompt, args.prompt_file)
    run_paths = run_once(
        prompt,
        runs_dir=args.runs_dir,
        artifacts_dir=args.artifacts_dir,
        run_id=args.run_id,
        model=args.model,
    )
    print(
        json.dumps(
            {
                "run_id": run_paths.run_id,
                "run_dir": str(run_paths.run_root),
                "project_dir": str(run_paths.project_root),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
