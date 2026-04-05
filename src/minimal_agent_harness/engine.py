from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from minimal_agent_harness.tools import EchoTool, Tool, build_core_tools


@dataclass
class RunContext:
    instruction: str
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolAction:
    tool_name: str
    arguments: dict[str, Any]


@dataclass
class FinishAction:
    response: str


Action = ToolAction | FinishAction


class Backend(Protocol):
    def next_action(self, context: RunContext) -> Action:
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


class AgentRunner:
    def __init__(self, backend: Backend, tools: list[Tool], max_steps: int = 5):
        self._backend = backend
        self._tools = {tool.name: tool for tool in tools}
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


def build_default_runner() -> AgentRunner:
    return AgentRunner(backend=ScriptedBackend(), tools=build_core_tools(Path.cwd()))
