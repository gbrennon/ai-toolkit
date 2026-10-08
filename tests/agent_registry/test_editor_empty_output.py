from pathlib import Path
import subprocess

import pytest

from ai_toolkit.agent_registry.editor import RegistryEditor
from ai_toolkit.agent_registry.editor_invocation import EditorInvocation
from ai_toolkit.agent_registry.errors import EditorOutputEmptyError


class EmptyEditorRunner:
    def __call__(self, invocation: EditorInvocation) -> subprocess.CompletedProcess[str]:
        invocation.path.write_text("   ", encoding="utf-8")
        return subprocess.CompletedProcess(invocation.argv, 0, "", "")


def test_editor_rejects_empty_reviewed_output(tmp_path: Path) -> None:
    with pytest.raises(EditorOutputEmptyError):
        RegistryEditor(
            runner=EmptyEditorRunner(),
            environment={"EDITOR": "editor"},
        ).edit("draft", temporary_path=tmp_path / "AGENT.md")
