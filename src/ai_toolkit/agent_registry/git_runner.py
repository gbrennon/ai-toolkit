from typing import Protocol

from .git_invocation import GitInvocation
from .git_result import GitResult


class GitRunner(Protocol):
    """Run a described Git invocation without shell interpretation."""

    def __call__(self, invocation: GitInvocation) -> GitResult:
        """Return a subprocess result for the supplied Git invocation."""
        ...
