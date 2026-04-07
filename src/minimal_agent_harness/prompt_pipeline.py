from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from minimal_agent_harness.artifacts import PipelineRunPaths, build_run_paths, initialize_run_directory
from minimal_agent_harness.backends import OpenRouterChatClient, _extract_json_object
from minimal_agent_harness.config import load_dotenv_if_present
from minimal_agent_harness.stage_prompts import StagePrompt, load_stage_prompt


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
class StageMeta:
    stage: str
    backend_name: str
    model: str
    fallback_models: list[str] = field(default_factory=list)
    prompt_id: str = ""
    prompt_sha256: str = ""
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


VALID_CRITIC_VERDICTS = {"accept", "narrow", "reject"}


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


def _schema_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2)


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected non-empty string for {field_name}")
    return value


def _require_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"Expected list for {field_name}")
    items = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"Expected non-empty string items for {field_name}")
        items.append(item)
    return items


def _require_confidence(value: Any) -> float:
    if not isinstance(value, int | float):
        raise ValueError("Expected numeric confidence")
    resolved = float(value)
    if not 0.0 <= resolved <= 1.0:
        raise ValueError("Confidence must be between 0.0 and 1.0")
    return resolved


def _build_stage_meta(
    *,
    stage: str,
    model: str,
    fallback_models: list[str],
    prompt_asset: StagePrompt,
) -> StageMeta:
    return StageMeta(
        stage=stage,
        backend_name="openrouter",
        model=model,
        fallback_models=fallback_models,
        prompt_id=prompt_asset.prompt_id,
        prompt_sha256=prompt_asset.content_hash,
    )


def _write_stage_meta(path: Path, meta: StageMeta) -> None:
    path.write_text(json.dumps(asdict(meta), indent=2))


def _load_existing_run(run_dir: str | Path) -> PipelineRunPaths:
    run_root = Path(run_dir)
    return build_run_paths(base_dir=run_root.parent, run_id=run_root.name)


def _render_prompt(stage: str, **kwargs: str) -> tuple[StagePrompt, str]:
    prompt_asset = load_stage_prompt(stage)
    return prompt_asset, prompt_asset.render(**kwargs)


def _run_stage_completion(
    *,
    stage: str,
    model: str,
    fallback_models: list[str],
    client: StageClient,
    prompt_kwargs: dict[str, str],
) -> tuple[StagePrompt, str]:
    prompt_asset, prompt_text = _render_prompt(stage, **prompt_kwargs)
    output = client.create_completion(
        model=model,
        prompt=prompt_text,
        fallback_models=fallback_models,
    )
    return prompt_asset, output


def _parse_evaluator_diagnosis(payload: dict[str, Any]) -> EvaluatorDiagnosis:
    return EvaluatorDiagnosis(
        summary=_require_string(payload.get("summary"), "summary"),
        observed_strengths=_require_string_list(payload.get("observed_strengths"), "observed_strengths"),
        observed_weaknesses=_require_string_list(payload.get("observed_weaknesses"), "observed_weaknesses"),
        missing_capabilities=_require_string_list(payload.get("missing_capabilities"), "missing_capabilities"),
        suggested_interventions=_require_string_list(
            payload.get("suggested_interventions"), "suggested_interventions"
        ),
        confidence=_require_confidence(payload.get("confidence")),
    )


def _parse_critic_review(payload: dict[str, Any]) -> CriticReview:
    verdict = _require_string(payload.get("verdict"), "verdict")
    if verdict not in VALID_CRITIC_VERDICTS:
        raise ValueError(f"Invalid critic verdict: {verdict}")
    return CriticReview(
        verdict=verdict,
        summary=_require_string(payload.get("summary"), "summary"),
        approved_interventions=_require_string_list(
            payload.get("approved_interventions"), "approved_interventions"
        ),
        concerns=_require_string_list(payload.get("concerns"), "concerns"),
        confidence=_require_confidence(payload.get("confidence")),
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

    prompt_asset, output_text = _run_stage_completion(
        stage="generator",
        model=resolved_model,
        fallback_models=resolved_fallbacks,
        client=resolved_client,
        prompt_kwargs={"topic_text": topic_text.strip()},
    )
    run_paths.generator_output_file.write_text(output_text.strip() + "\n")
    _write_stage_meta(
        run_paths.generator_meta_file,
        _build_stage_meta(
            stage="generator",
            model=resolved_model,
            fallback_models=resolved_fallbacks,
            prompt_asset=prompt_asset,
        ),
    )
    return run_paths


def run_evaluator(
    run_dir: str | Path,
    *,
    model: str | None = None,
    fallback_models: list[str] | None = None,
    client: StageClient | None = None,
) -> Path:
    run_paths = _load_existing_run(run_dir)
    output_text = run_paths.generator_output_file.read_text()
    topic_text = run_paths.topic_file.read_text()
    resolved_model = model or _default_model()
    resolved_fallbacks = fallback_models if fallback_models is not None else _default_fallback_models()
    resolved_client = client or build_stage_client()

    prompt_asset, raw = _run_stage_completion(
        stage="evaluator",
        model=resolved_model,
        fallback_models=resolved_fallbacks,
        client=resolved_client,
        prompt_kwargs={
            "schema_json": _schema_json(
                {
                    "summary": "string",
                    "observed_strengths": ["string"],
                    "observed_weaknesses": ["string"],
                    "missing_capabilities": ["string"],
                    "suggested_interventions": ["string"],
                    "confidence": 0.0,
                }
            ),
            "topic_text": topic_text.strip(),
            "output_text": output_text.strip(),
        },
    )
    diagnosis = _parse_evaluator_diagnosis(_extract_json_object(raw))
    run_paths.evaluator_diagnosis_file.write_text(json.dumps(asdict(diagnosis), indent=2))
    _write_stage_meta(
        run_paths.evaluator_meta_file,
        _build_stage_meta(
            stage="evaluator",
            model=resolved_model,
            fallback_models=resolved_fallbacks,
            prompt_asset=prompt_asset,
        ),
    )
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
    run_paths = _load_existing_run(run_dir)
    topic_text = run_paths.topic_file.read_text()
    output_text = run_paths.generator_output_file.read_text()
    diagnosis_text = run_paths.evaluator_diagnosis_file.read_text()
    resolved_model = model or _default_model()
    resolved_fallbacks = fallback_models if fallback_models is not None else _default_fallback_models()
    resolved_client = client or build_stage_client()

    prompt_asset, raw = _run_stage_completion(
        stage="critic",
        model=resolved_model,
        fallback_models=resolved_fallbacks,
        client=resolved_client,
        prompt_kwargs={
            "schema_json": _schema_json(
                {
                    "verdict": "accept | narrow | reject",
                    "summary": "string",
                    "approved_interventions": ["string"],
                    "concerns": ["string"],
                    "confidence": 0.0,
                }
            ),
            "topic_text": topic_text.strip(),
            "output_text": output_text.strip(),
            "diagnosis_text": diagnosis_text.strip(),
        },
    )
    review = _parse_critic_review(_extract_json_object(raw))
    run_paths.critic_review_file.write_text(json.dumps(asdict(review), indent=2))
    _write_stage_meta(
        run_paths.critic_meta_file,
        _build_stage_meta(
            stage="critic",
            model=resolved_model,
            fallback_models=resolved_fallbacks,
            prompt_asset=prompt_asset,
        ),
    )
    run_paths.critic_notes_file.write_text(
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
    return run_paths.critic_review_file
