import subprocess
from typing import Protocol

from .editor_invocation import EditorInvocation


class EditorRunner(Protocol):
    """Run one described editor command without shell interpretation."""

    def __call__(self, invocation: EditorInvocation) -> subprocess.CompletedProcess[str]:
        """Return the completed process result for one invocation."""
        ...
