from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from string import Template


PROMPTS_PACKAGE = "minimal_agent_harness.prompts"
VALID_STAGES = ("generator", "evaluator", "critic")


@dataclass(frozen=True)
class StagePrompt:
    stage: str
    package: str
    resource_name: str
    template_text: str
    content_hash: str

    @property
    def prompt_id(self) -> str:
        return f"{self.package}/{self.resource_name}"

    def render(self, **kwargs: str) -> str:
        return Template(self.template_text).substitute(**kwargs).strip() + "\n"


def load_stage_prompt(stage: str) -> StagePrompt:
    if stage not in VALID_STAGES:
        raise ValueError(f"Unknown stage prompt: {stage}")

    resource_name = f"{stage}.md"
    prompt_file = files(PROMPTS_PACKAGE).joinpath(resource_name)
    if not prompt_file.is_file():
        raise FileNotFoundError(f"Missing stage prompt asset: {PROMPTS_PACKAGE}/{resource_name}")

    template_text = prompt_file.read_text(encoding="utf-8")
    return StagePrompt(
        stage=stage,
        package=PROMPTS_PACKAGE,
        resource_name=resource_name,
        template_text=template_text,
        content_hash=sha256(template_text.encode("utf-8")).hexdigest(),
    )
