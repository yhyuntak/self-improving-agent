from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class PipelineRunPaths:
    run_id: str
    root: Path
    topic_file: Path
    generator_dir: Path
    generator_output_file: Path
    generator_meta_file: Path
    evaluator_dir: Path
    evaluator_diagnosis_file: Path
    evaluator_notes_file: Path
    critic_dir: Path
    critic_review_file: Path
    critic_notes_file: Path


def default_run_id(prefix: str = "run") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}"


def build_run_paths(base_dir: str | Path = "artifacts/runs", run_id: str | None = None) -> PipelineRunPaths:
    resolved_run_id = run_id or default_run_id()
    root = Path(base_dir) / resolved_run_id
    return PipelineRunPaths(
        run_id=resolved_run_id,
        root=root,
        topic_file=root / "topic.md",
        generator_dir=root / "generator",
        generator_output_file=root / "generator" / "output.md",
        generator_meta_file=root / "generator" / "meta.json",
        evaluator_dir=root / "evaluator",
        evaluator_diagnosis_file=root / "evaluator" / "diagnosis.json",
        evaluator_notes_file=root / "evaluator" / "notes.md",
        critic_dir=root / "critic",
        critic_review_file=root / "critic" / "review.json",
        critic_notes_file=root / "critic" / "notes.md",
    )


def initialize_run_directory(
    topic_text: str,
    *,
    base_dir: str | Path = "artifacts/runs",
    run_id: str | None = None,
) -> PipelineRunPaths:
    run_paths = build_run_paths(base_dir=base_dir, run_id=run_id)
    run_paths.generator_dir.mkdir(parents=True, exist_ok=True)
    run_paths.evaluator_dir.mkdir(parents=True, exist_ok=True)
    run_paths.critic_dir.mkdir(parents=True, exist_ok=True)
    run_paths.topic_file.write_text(topic_text.strip() + "\n")
    return run_paths
