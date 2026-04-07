from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from minimal_agent_harness.artifacts import PipelineRunPaths, initialize_run_directory
from minimal_agent_harness.backends import OpenRouterChatClient, _extract_json_object
from minimal_agent_harness.config import load_dotenv_if_present


class StageClient(Protocol):
    def create_completion(
        self,
        *,
        model: str,
        prompt: str,
        fallback_models: list[str] | None = None,
    ) -> str:
        ...


@dataclass
class GeneratorMeta:
    stage: str
    backend_name: str
    model: str
    fallback_models: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EvaluatorDiagnosis:
    summary: str
    observed_strengths: list[str]
    observed_weaknesses: list[str]
    missing_capabilities: list[str]
    suggested_interventions: list[str]
    confidence: float


@dataclass
class CriticReview:
    verdict: str
    summary: str
    approved_interventions: list[str]
    concerns: list[str]
    confidence: float


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def _default_model() -> str:
    load_dotenv_if_present()
    return os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus:free")


def _default_fallback_models() -> list[str]:
    load_dotenv_if_present()
    raw = os.getenv("OPENROUTER_FALLBACK_MODELS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_stage_client() -> OpenRouterChatClient:
    load_dotenv_if_present()
    return OpenRouterChatClient(
        site_url=os.getenv("OPENROUTER_SITE_URL"),
        app_name=os.getenv("OPENROUTER_APP_NAME"),
    )


def run_generator(
    topic_text: str,
    *,
    base_dir: str | Path = "artifacts/runs",
    run_id: str | None = None,
    model: str | None = None,
    fallback_models: list[str] | None = None,
    client: StageClient | None = None,
) -> PipelineRunPaths:
    run_paths = initialize_run_directory(topic_text, base_dir=base_dir, run_id=run_id)
    resolved_model = model or _default_model()
    resolved_fallbacks = fallback_models if fallback_models is not None else _default_fallback_models()
    resolved_client = client or build_stage_client()

    prompt = "\n".join(
        [
            "You are a generator stage in an artifact-driven workflow.",
            "Write a useful first-pass markdown deliverable for the topic below.",
            "Do not return JSON.",
            "Topic:",
            topic_text.strip(),
        ]
    )
    output_text = resolved_client.create_completion(
        model=resolved_model,
        prompt=prompt,
        fallback_models=resolved_fallbacks,
    )

    run_paths.generator_output_file.write_text(output_text.strip() + "\n")
    run_paths.generator_meta_file.write_text(
        json.dumps(
            asdict(
                GeneratorMeta(
                    stage="generator",
                    backend_name="openrouter",
                    model=resolved_model,
                    fallback_models=resolved_fallbacks,
                )
            ),
            indent=2,
        )
    )
    return run_paths


def run_evaluator(
    run_dir: str | Path,
    *,
    model: str | None = None,
    fallback_models: list[str] | None = None,
    client: StageClient | None = None,
) -> Path:
    run_paths = initialize_run_directory(
        Path(run_dir, "topic.md").read_text(),
        base_dir=Path(run_dir).parent,
        run_id=Path(run_dir).name,
    )
    output_text = run_paths.generator_output_file.read_text()
    topic_text = run_paths.topic_file.read_text()
    resolved_model = model or _default_model()
    resolved_fallbacks = fallback_models if fallback_models is not None else _default_fallback_models()
    resolved_client = client or build_stage_client()

    prompt = "\n".join(
        [
            "You are the evaluator stage in an artifact-driven workflow.",
            "Read the topic and generated markdown, then return one JSON object only.",
            "Schema:",
            json.dumps(
                {
                    "summary": "string",
                    "observed_strengths": ["string"],
                    "observed_weaknesses": ["string"],
                    "missing_capabilities": ["string"],
                    "suggested_interventions": ["string"],
                    "confidence": 0.0,
                },
                indent=2,
            ),
            "Topic:",
            topic_text.strip(),
            "Generated output:",
            output_text.strip(),
        ]
    )
    raw = resolved_client.create_completion(
        model=resolved_model,
        prompt=prompt,
        fallback_models=resolved_fallbacks,
    )
    payload = _extract_json_object(raw)
    diagnosis = EvaluatorDiagnosis(
        summary=str(payload["summary"]),
        observed_strengths=[str(item) for item in payload.get("observed_strengths", [])],
        observed_weaknesses=[str(item) for item in payload.get("observed_weaknesses", [])],
        missing_capabilities=[str(item) for item in payload.get("missing_capabilities", [])],
        suggested_interventions=[str(item) for item in payload.get("suggested_interventions", [])],
        confidence=float(payload.get("confidence", 0.0)),
    )
    run_paths.evaluator_diagnosis_file.write_text(json.dumps(asdict(diagnosis), indent=2))
    run_paths.evaluator_notes_file.write_text(
        "\n".join(
            [
                "# Evaluation Notes",
                "",
                f"Summary: {diagnosis.summary}",
                "",
                "## Strengths",
                *_bullet_lines(diagnosis.observed_strengths),
                "",
                "## Weaknesses",
                *_bullet_lines(diagnosis.observed_weaknesses),
                "",
                "## Suggested Interventions",
                *_bullet_lines(diagnosis.suggested_interventions),
            ]
        )
        + "\n"
    )
    return run_paths.evaluator_diagnosis_file


def run_critic(
    run_dir: str | Path,
    *,
    model: str | None = None,
    fallback_models: list[str] | None = None,
    client: StageClient | None = None,
) -> Path:
    run_root = Path(run_dir)
    topic_text = (run_root / "topic.md").read_text()
    output_text = (run_root / "generator" / "output.md").read_text()
    diagnosis_text = (run_root / "evaluator" / "diagnosis.json").read_text()
    resolved_model = model or _default_model()
    resolved_fallbacks = fallback_models if fallback_models is not None else _default_fallback_models()
    resolved_client = client or build_stage_client()

    prompt = "\n".join(
        [
            "You are the critic stage in an artifact-driven workflow.",
            "Read the topic, generated output, and diagnosis, then return one JSON object only.",
            "Verdict must be one of: accept, narrow, reject.",
            "Schema:",
            json.dumps(
                {
                    "verdict": "accept | narrow | reject",
                    "summary": "string",
                    "approved_interventions": ["string"],
                    "concerns": ["string"],
                    "confidence": 0.0,
                },
                indent=2,
            ),
            "Topic:",
            topic_text.strip(),
            "Generated output:",
            output_text.strip(),
            "Diagnosis JSON:",
            diagnosis_text.strip(),
        ]
    )
    raw = resolved_client.create_completion(
        model=resolved_model,
        prompt=prompt,
        fallback_models=resolved_fallbacks,
    )
    payload = _extract_json_object(raw)
    review = CriticReview(
        verdict=str(payload["verdict"]),
        summary=str(payload["summary"]),
        approved_interventions=[str(item) for item in payload.get("approved_interventions", [])],
        concerns=[str(item) for item in payload.get("concerns", [])],
        confidence=float(payload.get("confidence", 0.0)),
    )
    review_file = run_root / "critic" / "review.json"
    notes_file = run_root / "critic" / "notes.md"
    review_file.write_text(json.dumps(asdict(review), indent=2))
    notes_file.write_text(
        "\n".join(
            [
                "# Critic Review",
                "",
                f"Verdict: {review.verdict}",
                "",
                f"Summary: {review.summary}",
                "",
                "## Approved Interventions",
                *_bullet_lines(review.approved_interventions),
                "",
                "## Concerns",
                *_bullet_lines(review.concerns),
            ]
        )
        + "\n"
    )
    return review_file
