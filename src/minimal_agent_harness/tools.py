from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class Tool(Protocol):
    name: str

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass
class WorkspaceTool:
    root: Path

    def _resolve_path(self, raw_path: str) -> Path:
        candidate = (self.root / raw_path).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError as exc:
            raise ValueError(
                f"Path escapes workspace: {raw_path}. Use a path under {self.root}."
            ) from exc
        return candidate


class EchoTool:
    name = "echo"

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        text = str(arguments.get("text", ""))
        return {"ok": True, "echoed_text": text}


@dataclass
class ListFilesTool(WorkspaceTool):
    name = "list_files"

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_path = str(arguments.get("path", "."))
        target = self._resolve_path(raw_path)
        if not target.exists():
            return {
                "ok": False,
                "error": f"Directory not found: {raw_path}. Create it first or choose an existing path.",
            }
        if not target.is_dir():
            return {
                "ok": False,
                "error": f"Not a directory: {raw_path}. Use a directory path for list_files.",
            }

        entries = []
        for entry in sorted(target.iterdir(), key=lambda item: item.name):
            relative = entry.relative_to(self.root).as_posix()
            entries.append(
                {
                    "path": relative,
                    "type": "directory" if entry.is_dir() else "file",
                }
            )

        return {"ok": True, "entries": entries}


@dataclass
class ReadFileTool(WorkspaceTool):
    name = "read_file"

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_path = str(arguments.get("path", ""))
        if not raw_path:
            return {"ok": False, "error": "Missing path. Provide a file path to read."}

        target = self._resolve_path(raw_path)
        if not target.exists():
            return {
                "ok": False,
                "error": f"File not found: {raw_path}. Check the path or create the file first.",
            }
        if not target.is_file():
            return {
                "ok": False,
                "error": f"Not a file: {raw_path}. Use read_file only with files.",
            }

        return {"ok": True, "content": target.read_text()}


@dataclass
class WriteFileTool(WorkspaceTool):
    name = "write_file"

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_path = str(arguments.get("path", ""))
        content = str(arguments.get("content", ""))
        if not raw_path:
            return {"ok": False, "error": "Missing path. Provide a file path to write."}

        target = self._resolve_path(raw_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return {
            "ok": True,
            "path": target.relative_to(self.root).as_posix(),
            "bytes_written": len(content.encode()),
        }


@dataclass
class RunShellTool(WorkspaceTool):
    name = "run_shell"
    timeout_sec: int = 10

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        command = str(arguments.get("command", "")).strip()
        if not command:
            return {"ok": False, "error": "Missing command. Provide a shell command to run."}

        completed = subprocess.run(
            command,
            cwd=self.root,
            shell=True,
            text=True,
            capture_output=True,
            timeout=self.timeout_sec,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "(no stderr)"
            return {
                "ok": False,
                "error": (
                    f"Command failed with exit code {completed.returncode}: {command}. "
                    f"stderr: {stderr}"
                ),
            }

        return {
            "ok": True,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "exit_code": completed.returncode,
        }


def build_core_tools(root: str | Path) -> list[Tool]:
    workspace_root = Path(root).resolve()
    return [
        EchoTool(),
        ListFilesTool(workspace_root),
        ReadFileTool(workspace_root),
        WriteFileTool(workspace_root),
        RunShellTool(workspace_root),
    ]
