import json

from minimal_agent_harness.engine import build_default_runner


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
