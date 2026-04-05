import json
import pytest

from minimal_agent_harness.engine import AgentRunner, FinishAction, build_default_runner
from minimal_agent_harness.tools import EchoTool


class BadBackend:
    def next_action(self, context):
        return FinishAction(response="done")


def test_runner_writes_tool_and_finish_events(tmp_path):
    log_file = tmp_path / "run.json"

    response = build_default_runner().run(
        instruction="create a sample result",
        log_file=str(log_file),
    )

    assert "Completed sample run" in response

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
