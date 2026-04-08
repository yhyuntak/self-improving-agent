import json
from pathlib import Path

import pytest

from agents.agent_cycle_state import (
    build_state_path,
    create_cycle_state,
    load_cycle_state,
    load_cycle_state_for_id,
    resolve_state_path,
    save_cycle_state,
)


def test_save_and_load_cycle_state_round_trip(tmp_path):
    state = create_cycle_state(
        cycle_id="cycle-001",
        benchmark_prompt_path="benchmarks/todo-list-project.txt",
        run_id="run-001",
        run_dir="runs/run-001",
        evaluation_path="runs/run-001/evaluation.json",
        critique_path="runs/run-001/critique.json",
        diagnosis="Tighten prompt text.",
        approved_change="Make output requirements more concrete.",
        status="awaiting_approval",
    )

    saved_path = save_cycle_state(state, tmp_path)

    assert saved_path == build_state_path("cycle-001", tmp_path)
    assert saved_path.exists()

    loaded = load_cycle_state_for_id("cycle-001", tmp_path)

    assert loaded == state


def test_load_cycle_state_rejects_invalid_status(tmp_path):
    path = build_state_path("cycle-002", tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "cycle_id": "cycle-002",
                "benchmark_prompt_path": "benchmarks/todo-list-project.txt",
                "run_id": "run-002",
                "run_dir": "runs/run-002",
                "evaluation_path": "runs/run-002/evaluation.json",
                "critique_path": "runs/run-002/critique.json",
                "diagnosis": "diagnosis",
                "approved_change": "change",
                "status": "not-real",
                "created_at": "2026-04-08T00:00:00+00:00",
                "updated_at": "2026-04-08T00:00:00+00:00",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_cycle_state(path, tmp_path)


def test_resolve_state_path_rejects_outside_paths(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError):
        resolve_state_path(outside, tmp_path)
