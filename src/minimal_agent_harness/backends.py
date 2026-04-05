from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from minimal_agent_harness.types import Action, FinishAction, RunContext, ToolAction


class LLMClient(Protocol):
    def create_completion(
        self,
        *,
        model: str,
        prompt: str,
        fallback_models: list[str] | None = None,
    ) -> str:
        ...


def _candidate_models(model: str, fallback_models: list[str] | None) -> list[str]:
    candidates = [model]
    if fallback_models:
        candidates.extend(fallback_models)
    return candidates


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(raw_text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(raw_text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("Model output did not contain a JSON object.")


@dataclass
class OpenRouterChatClient:
    api_key: str | None = None
    base_url: str = "https://openrouter.ai/api/v1"
    site_url: str | None = None
    app_name: str | None = None

    def create_completion(
        self,
        *,
        model: str,
        prompt: str,
        fallback_models: list[str] | None = None,
    ) -> str:
        from openai import OpenAI

        default_headers = {}
        if self.site_url:
            default_headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            default_headers["X-OpenRouter-Title"] = self.app_name

        client = OpenAI(
            api_key=self.api_key or os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", self.base_url),
            default_headers=default_headers or None,
        )
        failures: list[str] = []
        for candidate_model in _candidate_models(model, fallback_models):
            try:
                completion = client.chat.completions.create(
                    model=candidate_model,
                    messages=[{"role": "user", "content": prompt}],
                )
                message = completion.choices[0].message.content
                if not message:
                    raise ValueError("OpenRouter response did not include message content.")
                return message
            except Exception as exc:
                failures.append(f"{candidate_model}: {exc}")

        raise RuntimeError("All OpenRouter model candidates failed. " + " | ".join(failures))


@dataclass
class OpenRouterBackend:
    model: str
    client: LLMClient
    fallback_models: list[str] | None = None

    def next_action(self, context: RunContext) -> Action:
        prompt = self._build_prompt(context)
        raw_text = self.client.create_completion(
            model=self.model,
            prompt=prompt,
            fallback_models=self.fallback_models,
        )
        payload = _extract_json_object(raw_text)
        kind = payload.get("kind")

        if kind == "tool":
            tool_name = payload.get("tool_name")
            arguments = payload.get("arguments", {})
            if not isinstance(tool_name, str) or not isinstance(arguments, dict):
                raise ValueError("Tool actions require a string tool_name and object arguments.")
            return ToolAction(tool_name=tool_name, arguments=arguments)

        if kind == "finish":
            response = payload.get("response")
            if not isinstance(response, str):
                raise ValueError("Finish actions require a string response.")
            return FinishAction(response=response)

        raise ValueError(f"Unknown action kind from model output: {kind!r}")

    @staticmethod
    def _build_prompt(context: RunContext) -> str:
        tool_names = ["echo", "list_files", "read_file", "write_file", "run_shell"]
        prompt = {
            "task": "Choose the next harness action as strict JSON.",
            "instruction": context.instruction,
            "available_tools": tool_names,
            "previous_events": context.events,
            "rules": [
                "Return exactly one JSON object and no extra prose.",
                "Use {'kind':'tool','tool_name':string,'arguments':object} when another tool is needed.",
                "Use {'kind':'finish','response':string} only when the task is complete.",
                "Call at least one tool before finishing.",
            ],
        }
        return json.dumps(prompt, indent=2)
