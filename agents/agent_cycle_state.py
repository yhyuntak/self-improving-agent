from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR = Path(".codex/state/agent-cycles")
ALLOWED_STATUSES = {
    "review_running",
    "awaiting_approval",
    "approved",
    "apply_running",
    "improved",
    "failed",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_cycle_id(cycle_id: str) -> str:
    normalized = cycle_id.strip()
    if not normalized:
        raise ValueError("cycle_id must not be empty")
    if normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
        raise ValueError("cycle_id must be a simple name")
    return normalized


def build_state_dir(repo_root: str | Path = ".") -> Path:
    return Path(repo_root) / STATE_DIR


def build_state_path(cycle_id: str, repo_root: str | Path = ".") -> Path:
    return build_state_dir(repo_root) / f"{validate_cycle_id(cycle_id)}.json"


def resolve_state_path(path: str | Path, repo_root: str | Path = ".") -> Path:
    repo_root_path = Path(repo_root).resolve()
    state_dir = build_state_dir(repo_root_path).resolve()
    candidate = Path(path)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo_root_path / candidate).resolve()
    try:
        resolved.relative_to(state_dir)
    except ValueError as exc:
        raise ValueError("state path must stay inside .codex/state/agent-cycles") from exc
    if resolved.suffix != ".json":
        raise ValueError("state path must point to a .json file")
    return resolved


@dataclass(frozen=True)
class CycleState:
    cycle_id: str
    benchmark_prompt_path: str
    run_id: str
    run_dir: str
    evaluation_path: str
    critique_path: str
    diagnosis: str
    approved_change: str
    status: str
    created_at: str
    updated_at: str

    def to_payload(self) -> dict[str, str]:
        return asdict(self)


def validate_status(status: str) -> str:
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid cycle status: {status}")
    return status


def create_cycle_state(
    *,
    cycle_id: str,
    benchmark_prompt_path: str,
    status: str = "review_running",
    run_id: str = "",
    run_dir: str = "",
    evaluation_path: str = "",
    critique_path: str = "",
    diagnosis: str = "",
    approved_change: str = "",
    created_at: str | None = None,
    updated_at: str | None = None,
) -> CycleState:
    timestamp = utc_now()
    return CycleState(
        cycle_id=validate_cycle_id(cycle_id),
        benchmark_prompt_path=benchmark_prompt_path,
        run_id=run_id,
        run_dir=run_dir,
        evaluation_path=evaluation_path,
        critique_path=critique_path,
        diagnosis=diagnosis,
        approved_change=approved_change,
        status=validate_status(status),
        created_at=created_at or timestamp,
        updated_at=updated_at or timestamp,
    )


def save_cycle_state(state: CycleState, repo_root: str | Path = ".") -> Path:
    path = build_state_path(state.cycle_id, repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_payload(), indent=2) + "\n", encoding="utf-8")
    return path


def load_cycle_state(path: str | Path, repo_root: str | Path = ".") -> CycleState:
    resolved = resolve_state_path(path, repo_root)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return create_cycle_state(
        cycle_id=payload["cycle_id"],
        benchmark_prompt_path=payload["benchmark_prompt_path"],
        run_id=payload["run_id"],
        run_dir=payload["run_dir"],
        evaluation_path=payload["evaluation_path"],
        critique_path=payload["critique_path"],
        diagnosis=payload["diagnosis"],
        approved_change=payload["approved_change"],
        status=payload["status"],
        created_at=payload["created_at"],
        updated_at=payload["updated_at"],
    )


def load_cycle_state_for_id(cycle_id: str, repo_root: str | Path = ".") -> CycleState:
    return load_cycle_state(build_state_path(cycle_id, repo_root), repo_root)
