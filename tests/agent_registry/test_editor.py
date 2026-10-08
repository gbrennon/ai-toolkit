from pathlib import Path
import subprocess

import pytest

from ai_toolkit.agent_registry.editor import RegistryEditor
from ai_toolkit.agent_registry.errors import (
    EditorCommandEmptyError,
    EditorExecutionError,
    EditorNotConfiguredError,
)


class RecordingEditorRunner:
    def __init__(self, edited: str, returncode: int = 0) -> None:
        self.edited = edited
        self.returncode = returncode
        self.invocations: list[object] = []

    def __call__(self, invocation: object) -> subprocess.CompletedProcess[str]:
        self.invocations.append(invocation)
        path = getattr(invocation, "path")
        if self.returncode == 0:
            Path(path).write_text(self.edited, encoding="utf-8")
        return subprocess.CompletedProcess(
            getattr(invocation, "argv"), self.returncode, "editor output", "editor error"
        )


def test_editor_prefers_visual_and_parses_command_without_shell(tmp_path: Path) -> None:
    path = tmp_path / "AGENT.md"
    runner = RecordingEditorRunner("edited")
    editor = RegistryEditor(runner=runner, environment={"VISUAL": "visual --wait", "EDITOR": "editor"})

    result = editor.edit("draft", temporary_path=path)

    assert result == "edited"
    invocation = runner.invocations[0]
    assert getattr(invocation, "argv") == ("visual", "--wait", str(path))
    assert getattr(invocation, "shell") is False
    assert getattr(invocation, "capture_output") is True
    assert getattr(invocation, "text") is True


def test_editor_reports_missing_or_empty_configuration(tmp_path: Path) -> None:
    path = tmp_path / "AGENT.md"

    with pytest.raises(EditorNotConfiguredError):
        RegistryEditor(environment={}).edit("draft", temporary_path=path)
    with pytest.raises(EditorCommandEmptyError):
        RegistryEditor(environment={"EDITOR": "   "}).edit("draft", temporary_path=path)


def test_editor_reports_nonzero_exit_without_publishing_text(tmp_path: Path) -> None:
    path = tmp_path / "AGENT.md"
    runner = RecordingEditorRunner("edited", returncode=7)
    editor = RegistryEditor(runner=runner, environment={"EDITOR": "editor"})

    path.write_text("draft", encoding="utf-8")
    with pytest.raises(EditorExecutionError) as error:
        editor.edit("draft", temporary_path=path)

    assert "7" in str(error.value)
    assert path.read_text(encoding="utf-8") == "draft"
