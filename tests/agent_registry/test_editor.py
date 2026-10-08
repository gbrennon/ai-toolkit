from pathlib import Path
import subprocess

import pytest

from ai_toolkit.agent_registry.editor import RegistryEditor
from ai_toolkit.agent_registry.editor_invocation import EditorInvocation
from ai_toolkit.agent_registry.errors import (
    EditorCommandEmptyError,
    EditorExecutionError,
    EditorNotConfiguredError,
)


def test_editor_prefers_visual_and_parses_command_without_shell(tmp_path: Path) -> None:
    path = tmp_path / "AGENT.md"
    invocations: list[EditorInvocation] = []

    def runner(invocation: EditorInvocation) -> subprocess.CompletedProcess[str]:
        invocations.append(invocation)
        invocation.path.write_text("edited", encoding="utf-8")
        return subprocess.CompletedProcess(invocation.argv, 0, "", "")

    editor = RegistryEditor(
        runner=runner, environment={"VISUAL": "visual --wait", "EDITOR": "editor"}
    )
    result = editor.edit("draft", temporary_path=path)

    assert result == "edited"
    invocation = invocations[0]
    assert invocation.argv == ("visual", "--wait", str(path))
    assert invocation.shell is False
    assert invocation.capture_output is True
    assert invocation.text is True


def test_editor_reports_missing_or_empty_configuration(tmp_path: Path) -> None:
    path = tmp_path / "AGENT.md"

    with pytest.raises(EditorNotConfiguredError):
        RegistryEditor(environment={}).edit("draft", temporary_path=path)
    with pytest.raises(EditorCommandEmptyError):
        RegistryEditor(environment={"EDITOR": "   "}).edit("draft", temporary_path=path)


def test_editor_reports_nonzero_exit_without_publishing_text(tmp_path: Path) -> None:
    path = tmp_path / "AGENT.md"

    def runner(invocation: EditorInvocation) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(invocation.argv, 7, "", "editor failed")

    editor = RegistryEditor(runner=runner, environment={"EDITOR": "editor"})
    path.write_text("draft", encoding="utf-8")

    with pytest.raises(EditorExecutionError) as error:
        editor.edit("draft", temporary_path=path)

    assert "7" in str(error.value)
    assert path.read_text(encoding="utf-8") == "draft"
