from pathlib import Path

from minimal_agent_harness.tools import (
    ListFilesTool,
    ReadFileTool,
    RunShellTool,
    WriteFileTool,
)


def test_list_files_returns_workspace_relative_entries(tmp_path):
    (tmp_path / "alpha.txt").write_text("a")
    (tmp_path / "nested").mkdir()

    result = ListFilesTool(tmp_path).invoke({"path": "."})

    assert result["ok"] is True
    assert result["entries"] == [
        {"path": "alpha.txt", "type": "file"},
        {"path": "nested", "type": "directory"},
    ]


def test_read_file_returns_content(tmp_path):
    (tmp_path / "notes.txt").write_text("hello")

    result = ReadFileTool(tmp_path).invoke({"path": "notes.txt"})

    assert result == {"ok": True, "content": "hello"}


def test_write_file_creates_parent_directories(tmp_path):
    result = WriteFileTool(tmp_path).invoke(
        {"path": "deep/output.txt", "content": "written"}
    )

    assert result["ok"] is True
    assert (tmp_path / "deep" / "output.txt").read_text() == "written"


def test_run_shell_returns_stdout(tmp_path):
    result = RunShellTool(tmp_path).invoke({"command": "printf 'hello'"})

    assert result["ok"] is True
    assert result["stdout"] == "hello"
    assert result["exit_code"] == 0


def test_tool_failures_return_actionable_errors(tmp_path):
    missing_file = ReadFileTool(tmp_path).invoke({"path": "missing.txt"})
    bad_directory = ListFilesTool(tmp_path).invoke({"path": "missing-dir"})
    bad_command = RunShellTool(tmp_path).invoke({"command": "sh -c 'exit 3'"})

    assert missing_file == {
        "ok": False,
        "error": "File not found: missing.txt. Check the path or create the file first.",
    }
    assert bad_directory == {
        "ok": False,
        "error": "Directory not found: missing-dir. Create it first or choose an existing path.",
    }
    assert bad_command["ok"] is False
    assert "Command failed with exit code 3" in bad_command["error"]
