from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from openai import OpenAI

from agents.simple_prompt_agent.config import load_dotenv_if_present


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    root: Path
    input_file: Path
    output_file: Path
    events_file: Path
    meta_file: Path


@dataclass(frozen=True)
class AgentOutput:
    final_answer: str


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

    def create_response(
        self,
        *,
        model: str,
        fallback_models: list[str],
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        fake_response = os.getenv("SIMPLE_PROMPT_AGENT_FAKE_RESPONSE_JSON")
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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}"


def build_run_paths(runs_dir: str | Path = "runs", run_id: str | None = None) -> RunPaths:
    resolved_run_id = run_id or default_run_id()
    root = Path(runs_dir) / resolved_run_id
    return RunPaths(
        run_id=resolved_run_id,
        root=root,
        input_file=root / "input.json",
        output_file=root / "output.json",
        events_file=root / "events.jsonl",
        meta_file=root / "meta.json",
    )


def load_system_prompt() -> tuple[str, str]:
    prompt_path = Path(__file__).with_name("prompts") / "system.txt"
    prompt_text = prompt_path.read_text(encoding="utf-8").strip() + "\n"
    return prompt_text, sha256(prompt_text.encode("utf-8")).hexdigest()


def default_model() -> str:
    load_dotenv_if_present()
    return os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus:free")


def default_fallback_models() -> list[str]:
    load_dotenv_if_present()
    raw = os.getenv("OPENROUTER_FALLBACK_MODELS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def extract_json_object(text: str) -> dict[str, object]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Model response did not contain a JSON object")
    return json.loads(text[start : end + 1])


def parse_output(text: str) -> AgentOutput:
    payload = extract_json_object(text)
    final_answer = payload.get("final_answer")
    if not isinstance(final_answer, str) or not final_answer.strip():
        raise ValueError("final_answer must be a non-empty string")
    return AgentOutput(final_answer=final_answer)


def append_event(path: Path, event_type: str, **payload: object) -> None:
    event = {"event": event_type, "timestamp": utc_now(), **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def run_once(
    prompt: str,
    *,
    runs_dir: str | Path = "runs",
    run_id: str | None = None,
    model: str | None = None,
    fallback_models: list[str] | None = None,
    client: ModelClient | None = None,
) -> RunPaths:
    if not prompt.strip():
        raise ValueError("prompt must not be empty")

    run_paths = build_run_paths(runs_dir=runs_dir, run_id=run_id)
    run_paths.root.mkdir(parents=True, exist_ok=True)

    started_at = utc_now()
    resolved_model = model or default_model()
    resolved_fallbacks = fallback_models if fallback_models is not None else default_fallback_models()
    resolved_client = client or OpenRouterClient()
    system_prompt, prompt_sha256 = load_system_prompt()

    run_paths.input_file.write_text(
        json.dumps(
            {
                "run_id": run_paths.run_id,
                "agent_id": "simple_prompt_agent",
                "prompt": prompt,
                "created_at": started_at,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    append_event(run_paths.events_file, "run_started", run_id=run_paths.run_id, agent_id="simple_prompt_agent")
    append_event(run_paths.events_file, "user_message", role="user", content=prompt)

    raw_response = resolved_client.create_response(
        model=resolved_model,
        fallback_models=resolved_fallbacks,
        system_prompt=system_prompt,
        user_prompt=prompt,
    )
    output = parse_output(raw_response)

    run_paths.output_file.write_text(json.dumps(asdict(output), indent=2) + "\n", encoding="utf-8")
    append_event(run_paths.events_file, "assistant_message", role="assistant", content=output.final_answer)
    append_event(run_paths.events_file, "run_finished", status="ok")

    run_paths.meta_file.write_text(
        json.dumps(
            {
                "run_id": run_paths.run_id,
                "agent_id": "simple_prompt_agent",
                "model": resolved_model,
                "fallback_models": resolved_fallbacks,
                "system_prompt_path": "agents/simple_prompt_agent/prompts/system.txt",
                "system_prompt_sha256": prompt_sha256,
                "started_at": started_at,
                "finished_at": utc_now(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return run_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the simple prompt agent once")
    parser.add_argument("prompt", help="Prompt to send to the agent")
    parser.add_argument("--run-id", default=None, help="Optional run identifier")
    parser.add_argument("--runs-dir", default="runs", help="Directory for run artifacts")
    parser.add_argument("--model", default=None, help="Optional model override")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_paths = run_once(
        args.prompt,
        runs_dir=args.runs_dir,
        run_id=args.run_id,
        model=args.model,
    )
    print(json.dumps({"run_id": run_paths.run_id, "run_dir": str(run_paths.root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
