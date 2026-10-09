import subprocess
from typing import Protocol

from .hook_invocation import HookInvocation


class HookRunner(Protocol):
    """Run one described hook command without shell interpretation."""

    def __call__(self, invocation: HookInvocation) -> subprocess.CompletedProcess[str]:
        """Return the completed process result for one invocation."""
        ...
