from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from minimal_agent_harness.types import Action, FinishAction, RunContext, ToolAction


class LLMClient(Protocol):
    def create_response(self, *, model: str, prompt: str) -> str:
        ...


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
class OpenAIResponsesClient:
    api_key: str | None = None

    def create_response(self, *, model: str, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key or os.getenv("OPENAI_API_KEY"))
        response = client.responses.create(model=model, input=prompt)
        text = getattr(response, "output_text", None)
        if not text:
            raise ValueError("OpenAI response did not include output_text.")
        return text


@dataclass
class OpenAIBackend:
    model: str
    client: LLMClient

    def next_action(self, context: RunContext) -> Action:
        prompt = self._build_prompt(context)
        raw_text = self.client.create_response(model=self.model, prompt=prompt)
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
