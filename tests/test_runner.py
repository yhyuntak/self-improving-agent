import json
import pytest

from minimal_agent_harness.engine import AgentRunner, build_default_runner
from minimal_agent_harness.tools import EchoTool
from minimal_agent_harness.types import FinishAction


class BadBackend:
    def next_action(self, context):
        return FinishAction(response="done")


class EmptyFinishBackend:
    def next_action(self, context):
        if not context.tool_results:
            from minimal_agent_harness.types import ToolAction

            return ToolAction(tool_name="echo", arguments={"text": "before-empty-finish"})
        return FinishAction(response="")


def test_runner_writes_tool_and_finish_events(tmp_path):
    log_file = tmp_path / "run.json"

    response = build_default_runner().run(
        instruction="create a sample result",
        log_file=str(log_file),
    )

    assert response.strip()

    payload = json.loads(log_file.read_text())
    event_types = [event["type"] for event in payload["events"]]
    assert event_types == ["tool_call", "finish"]
    assert payload["events"][0]["tool_name"] == "echo"


def test_verifier_blocks_incorrect_result(tmp_path):
    log_file = tmp_path / "failed-run.json"
    runner = AgentRunner(backend=BadBackend(), tools=[EchoTool()], verifier=build_default_runner()._verifier)

    with pytest.raises(RuntimeError, match="at least one tool call is required"):
        runner.run(instruction="skip the tool call", log_file=str(log_file))

    payload = json.loads(log_file.read_text())
    assert payload["events"][-1]["type"] == "verification_failed"


def test_verifier_blocks_empty_finish_response(tmp_path):
    log_file = tmp_path / "empty-run.json"
    runner = AgentRunner(
        backend=EmptyFinishBackend(),
        tools=[EchoTool()],
        verifier=build_default_runner()._verifier,
    )

    with pytest.raises(RuntimeError, match="final response must not be empty"):
        runner.run(instruction="finish with nothing", log_file=str(log_file))

    payload = json.loads(log_file.read_text())
    assert payload["events"][-1]["type"] == "verification_failed"
