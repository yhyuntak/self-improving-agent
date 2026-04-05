from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunContext:
    instruction: str
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolAction:
    tool_name: str
    arguments: dict[str, Any]


@dataclass
class FinishAction:
    response: str


Action = ToolAction | FinishAction


@dataclass
class VerificationResult:
    ok: bool
    error: str | None = None
