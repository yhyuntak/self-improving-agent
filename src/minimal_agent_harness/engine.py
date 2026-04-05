from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from minimal_agent_harness.backends import OpenAIBackend, OpenAIResponsesClient
from minimal_agent_harness.tools import Tool, build_core_tools
from minimal_agent_harness.types import (
    Action,
    FinishAction,
    RunContext,
    ToolAction,
    VerificationResult,
)


class Backend(Protocol):
    def next_action(self, context: RunContext) -> Action:
        ...


class Verifier(Protocol):
    def verify(self, context: RunContext, response: str) -> VerificationResult:
        ...


class ScriptedBackend:
    """Deterministic backend used to prove the harness loop works."""

    def next_action(self, context: RunContext) -> Action:
        if not context.tool_results:
            return ToolAction(
                tool_name="echo",
                arguments={"text": f"Instruction received: {context.instruction}"},
            )

        echoed_text = context.tool_results[-1]["result"]["echoed_text"]
        return FinishAction(
            response=f"Completed sample run after tool call. Last tool output: {echoed_text}"
        )


class SampleRunVerifier:
    """Minimal verifier that ensures the harness produced a real tool-assisted result."""

    def verify(self, context: RunContext, response: str) -> VerificationResult:
        if not any(event["type"] == "tool_call" for event in context.events):
            return VerificationResult(
                ok=False,
                error="Verification failed: at least one tool call is required before finish.",
            )
        if "Completed sample run" not in response:
            return VerificationResult(
                ok=False,
                error="Verification failed: final response is missing the expected completion marker.",
            )
        return VerificationResult(ok=True)


def build_backend(
    backend_name: str = "scripted",
    model: str | None = None,
    client: object | None = None,
):
    if backend_name == "scripted":
        return ScriptedBackend()
    if backend_name == "openai":
        resolved_model = model or os.getenv("OPENAI_MODEL") or "gpt-5.4-mini"
        resolved_client = client if client is not None else OpenAIResponsesClient()
        return OpenAIBackend(model=resolved_model, client=resolved_client)
    raise ValueError(f"Unknown backend: {backend_name}")


class AgentRunner:
    def __init__(
        self,
        backend: Backend,
        tools: list[Tool],
        verifier: Verifier | None = None,
        max_steps: int = 5,
    ):
        self._backend = backend
        self._tools = {tool.name: tool for tool in tools}
        self._verifier = verifier
        self._max_steps = max_steps

    def run(self, instruction: str, log_file: str | None = None) -> str:
        context = RunContext(instruction=instruction)

        for step in range(1, self._max_steps + 1):
            action = self._backend.next_action(context)

            if isinstance(action, ToolAction):
                tool = self._tools.get(action.tool_name)
                if tool is None:
                    raise ValueError(f"Unknown tool requested: {action.tool_name}")

                result = tool.invoke(action.arguments)
                tool_event = {
                    "step": step,
                    "type": "tool_call",
                    "tool_name": action.tool_name,
                    "arguments": action.arguments,
                    "result": result,
                }
                context.events.append(tool_event)
                context.tool_results.append(tool_event)
                continue

            if self._verifier is not None:
                verification = self._verifier.verify(context, action.response)
                if not verification.ok:
                    context.events.append(
                        {
                            "step": step,
                            "type": "verification_failed",
                            "error": verification.error,
                        }
                    )
                    if log_file is not None:
                        self._write_log(log_file, context)
                    raise RuntimeError(verification.error or "Verification failed")

            finish_event = {
                "step": step,
                "type": "finish",
                "response": action.response,
            }
            context.events.append(finish_event)

            if log_file is not None:
                self._write_log(log_file, context)
            return action.response

        raise RuntimeError("Agent did not finish within max_steps")

    @staticmethod
    def _write_log(log_file: str, context: RunContext) -> None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "instruction": context.instruction,
            "events": context.events,
        }
        path.write_text(json.dumps(payload, indent=2))


def build_default_runner(
    workspace_root: str | Path | None = None,
    backend_name: str = "scripted",
    model: str | None = None,
    client: object | None = None,
) -> AgentRunner:
    workspace = Path.cwd() if workspace_root is None else Path(workspace_root)
    return AgentRunner(
        backend=build_backend(backend_name=backend_name, model=model, client=client),
        tools=build_core_tools(workspace),
        verifier=SampleRunVerifier(),
    )
