import pytest

from minimal_agent_harness.backends import OpenRouterBackend, _extract_json_object
from minimal_agent_harness.engine import build_backend
from minimal_agent_harness.types import FinishAction, RunContext, ToolAction


class FakeLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create_completion(self, *, model: str, prompt: str, fallback_models=None) -> str:
        self.calls.append(
            {"model": model, "prompt": prompt, "fallback_models": fallback_models}
        )
        return self.responses.pop(0)


class FallbackAwareClient:
    def __init__(self):
        self.calls = []

    def create_completion(self, *, model: str, prompt: str, fallback_models=None) -> str:
        self.calls.append(
            {"model": model, "prompt": prompt, "fallback_models": fallback_models}
        )
        if model == "qwen/qwen3.6-plus:free" and fallback_models:
            return "{\"kind\":\"finish\",\"response\":\"Completed sample run after tool call.\"}"
        return "{\"kind\":\"finish\",\"response\":\"Completed sample run after tool call.\"}"


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
    backend = OpenRouterBackend(
        model="qwen/qwen3.6-plus:free",
        client=client,
        fallback_models=[
            "stepfun/step-3.5-flash:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "google/gemma-4-31b-it",
        ],
    )
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
    assert client.calls[0]["model"] == "qwen/qwen3.6-plus:free"
    assert client.calls[0]["fallback_models"] == [
        "stepfun/step-3.5-flash:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-31b-it",
    ]


def test_build_backend_supports_openrouter_with_fake_client(monkeypatch):
    monkeypatch.setenv(
        "OPENROUTER_FALLBACK_MODELS",
        "stepfun/step-3.5-flash:free,nvidia/nemotron-3-super-120b-a12b:free,google/gemma-4-31b-it",
    )
    backend = build_backend(
        backend_name="openrouter",
        model="qwen/qwen3.6-plus:free",
        client=FakeLLMClient(
            ["{\"kind\":\"finish\",\"response\":\"Completed sample run after tool call.\"}"]
        ),
    )
    assert isinstance(backend, OpenRouterBackend)
    assert backend.fallback_models == [
        "stepfun/step-3.5-flash:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-31b-it",
    ]


def test_openrouter_backend_passes_fallback_chain_to_client():
    client = FallbackAwareClient()
    backend = OpenRouterBackend(
        model="qwen/qwen3.6-plus:free",
        client=client,
        fallback_models=[
            "stepfun/step-3.5-flash:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "google/gemma-4-31b-it",
        ],
    )

    action = backend.next_action(RunContext(instruction="finish immediately"))

    assert action == FinishAction(response="Completed sample run after tool call.")
    assert client.calls[0]["fallback_models"] == [
        "stepfun/step-3.5-flash:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-31b-it",
    ]


def test_build_backend_rejects_unknown_backend():
    with pytest.raises(ValueError, match="Unknown backend"):
        build_backend("invalid")
