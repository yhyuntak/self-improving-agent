import pytest

from minimal_agent_harness.backends import OpenRouterBackend, _extract_json_object
from minimal_agent_harness.engine import build_backend
from minimal_agent_harness.types import FinishAction, RunContext, ToolAction


class FakeLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create_completion(self, *, model: str, prompt: str) -> str:
        self.calls.append({"model": model, "prompt": prompt})
        return self.responses.pop(0)


def test_extract_json_object_ignores_wrapping_text():
    payload = _extract_json_object("prefix\n{\"kind\":\"finish\",\"response\":\"done\"}\nsuffix")
    assert payload == {"kind": "finish", "response": "done"}


def test_openrouter_backend_returns_tool_then_finish():
    client = FakeLLMClient(
        [
            "{\"kind\":\"tool\",\"tool_name\":\"echo\",\"arguments\":{\"text\":\"hello\"}}",
            "{\"kind\":\"finish\",\"response\":\"Completed sample run after tool call. Last tool output: hello\"}",
        ]
    )
    backend = OpenRouterBackend(model="openai/gpt-oss-20b", client=client)
    context = RunContext(instruction="say hello")

    first = backend.next_action(context)
    assert first == ToolAction(tool_name="echo", arguments={"text": "hello"})

    context.events.append(
        {
            "step": 1,
            "type": "tool_call",
            "tool_name": "echo",
            "arguments": {"text": "hello"},
            "result": {"ok": True, "echoed_text": "hello"},
        }
    )

    second = backend.next_action(context)
    assert second == FinishAction(
        response="Completed sample run after tool call. Last tool output: hello"
    )
    assert client.calls[0]["model"] == "openai/gpt-oss-20b"


def test_build_backend_supports_openrouter_with_fake_client():
    backend = build_backend(
        backend_name="openrouter",
        model="openai/gpt-oss-20b",
        client=FakeLLMClient(
            ["{\"kind\":\"finish\",\"response\":\"Completed sample run after tool call.\"}"]
        ),
    )
    assert isinstance(backend, OpenRouterBackend)


def test_build_backend_rejects_unknown_backend():
    with pytest.raises(ValueError, match="Unknown backend"):
        build_backend("invalid")
