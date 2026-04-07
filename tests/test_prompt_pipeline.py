import json
import subprocess
import sys

import pytest

from minimal_agent_harness.artifacts import build_run_paths, initialize_run_directory
from minimal_agent_harness.prompt_pipeline import run_critic, run_evaluator, run_generator
from minimal_agent_harness.stage_prompts import load_stage_prompt


class FakeStageClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create_completion(self, *, model: str, prompt: str, fallback_models=None) -> str:
        self.calls.append(
            {"model": model, "prompt": prompt, "fallback_models": fallback_models}
        )
        return self.outputs.pop(0)


def test_initialize_run_directory_creates_contract(tmp_path):
    run_paths = initialize_run_directory(
        "Build a tiny landing page for a note-taking app.",
        base_dir=tmp_path,
        run_id="run-test",
    )

    assert run_paths.root == tmp_path / "run-test"
    assert run_paths.topic_file.read_text().strip() == "Build a tiny landing page for a note-taking app."
    assert run_paths.generator_dir.exists()
    assert run_paths.evaluator_dir.exists()
    assert run_paths.critic_dir.exists()


def test_stage_prompt_assets_load_for_all_stages():
    for stage in ("generator", "evaluator", "critic"):
        prompt_asset = load_stage_prompt(stage)
        assert prompt_asset.stage == stage
        assert prompt_asset.prompt_id.endswith(f"{stage}.md")
        assert prompt_asset.content_hash
        assert prompt_asset.template_text.strip()


def test_missing_stage_prompt_asset_fails(monkeypatch):
    from minimal_agent_harness import stage_prompts

    class DummyPromptFile:
        def is_file(self):
            return False

    class DummyResourceRoot:
        def joinpath(self, name):
            return DummyPromptFile()

    monkeypatch.setattr(stage_prompts, "files", lambda package: DummyResourceRoot())

    with pytest.raises(FileNotFoundError):
        stage_prompts.load_stage_prompt("generator")


def test_pipeline_stages_write_expected_artifacts(tmp_path):
    client = FakeStageClient(
        [
            "# Draft\n\nA first-pass product concept.",
            json.dumps(
                {
                    "summary": "Needs clearer structure.",
                    "observed_strengths": ["Clear topic match"],
                    "observed_weaknesses": ["Weak structure"],
                    "missing_capabilities": ["Outline discipline"],
                    "suggested_interventions": ["Add a pre-write outline rule"],
                    "confidence": 0.7,
                }
            ),
            json.dumps(
                {
                    "verdict": "accept",
                    "summary": "Reasonable diagnosis.",
                    "approved_interventions": ["Add a pre-write outline rule"],
                    "concerns": ["Keep it minimal"],
                    "confidence": 0.8,
                }
            ),
        ]
    )

    run_paths = run_generator(
        "Design a focused note-taking app homepage.",
        base_dir=tmp_path,
        run_id="pipeline-run",
        client=client,
        model="test-model",
        fallback_models=[],
    )
    run_evaluator(run_paths.root, client=client, model="test-model", fallback_models=[])
    run_critic(run_paths.root, client=client, model="test-model", fallback_models=[])

    diagnosis = json.loads(run_paths.evaluator_diagnosis_file.read_text())
    review = json.loads(run_paths.critic_review_file.read_text())
    generator_meta = json.loads(run_paths.generator_meta_file.read_text())
    evaluator_meta = json.loads(run_paths.evaluator_meta_file.read_text())
    critic_meta = json.loads(run_paths.critic_meta_file.read_text())

    assert run_paths.generator_output_file.exists()
    assert diagnosis["summary"] == "Needs clearer structure."
    assert review["verdict"] == "accept"
    assert generator_meta["prompt_id"].endswith("generator.md")
    assert evaluator_meta["prompt_id"].endswith("evaluator.md")
    assert critic_meta["prompt_id"].endswith("critic.md")
    assert len(client.calls) == 3


def test_pipeline_cli_runs_end_to_end_with_real_modules(tmp_path):
    topic = "Draft a tiny concept note for a habit tracking product."
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "from minimal_agent_harness.prompt_pipeline import run_generator, run_evaluator, run_critic",
                    "from tests.test_prompt_pipeline import FakeStageClient",
                    "client = FakeStageClient([",
                    "  '# Draft\\n\\nGenerated content.',",
                    "  '{\"summary\":\"ok\",\"observed_strengths\":[\"fit\"],\"observed_weaknesses\":[\"brevity\"],\"missing_capabilities\":[\"structure\"],\"suggested_interventions\":[\"outline\"],\"confidence\":0.6}',",
                    "  '{\"verdict\":\"narrow\",\"summary\":\"tighten scope\",\"approved_interventions\":[\"outline\"],\"concerns\":[\"avoid feature creep\"],\"confidence\":0.7}'",
                    "])",
                    f"run = run_generator({topic!r}, base_dir={str(tmp_path)!r}, run_id='cli-run', client=client, model='test-model', fallback_models=[])",
                    "run_evaluator(run.root, client=client, model='test-model', fallback_models=[])",
                    "run_critic(run.root, client=client, model='test-model', fallback_models=[])",
                    "print(run.root)",
                ]
            ),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    run_dir = result.stdout.strip()
    assert (build_run_paths(tmp_path, 'cli-run').generator_output_file).exists()
    assert (build_run_paths(tmp_path, 'cli-run').evaluator_meta_file).exists()
    assert (build_run_paths(tmp_path, 'cli-run').critic_review_file).exists()
    assert (build_run_paths(tmp_path, 'cli-run').critic_meta_file).exists()


def test_evaluator_rejects_invalid_json_shape(tmp_path):
    client = FakeStageClient(
        [
            "# Draft\n\nGenerated content.",
            json.dumps(
                {
                    "summary": "Missing the rest of the schema.",
                    "observed_strengths": ["fit"],
                }
            ),
        ]
    )

    run_paths = run_generator(
        "Design a focused note-taking app homepage.",
        base_dir=tmp_path,
        run_id="invalid-evaluator",
        client=client,
        model="test-model",
        fallback_models=[],
    )

    with pytest.raises(ValueError):
        run_evaluator(run_paths.root, client=client, model="test-model", fallback_models=[])


def test_critic_rejects_invalid_verdict(tmp_path):
    client = FakeStageClient(
        [
            "# Draft\n\nGenerated content.",
            json.dumps(
                {
                    "summary": "Needs clearer structure.",
                    "observed_strengths": ["Clear topic match"],
                    "observed_weaknesses": ["Weak structure"],
                    "missing_capabilities": ["Outline discipline"],
                    "suggested_interventions": ["Add a pre-write outline rule"],
                    "confidence": 0.7,
                }
            ),
            json.dumps(
                {
                    "verdict": "maybe",
                    "summary": "Unclear call.",
                    "approved_interventions": ["Add a pre-write outline rule"],
                    "concerns": ["Keep it minimal"],
                    "confidence": 0.8,
                }
            ),
        ]
    )

    run_paths = run_generator(
        "Design a focused note-taking app homepage.",
        base_dir=tmp_path,
        run_id="invalid-critic",
        client=client,
        model="test-model",
        fallback_models=[],
    )
    run_evaluator(run_paths.root, client=client, model="test-model", fallback_models=[])

    with pytest.raises(ValueError):
        run_critic(run_paths.root, client=client, model="test-model", fallback_models=[])
