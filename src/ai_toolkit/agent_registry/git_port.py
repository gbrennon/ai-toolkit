from pathlib import Path
from typing import Protocol


class GitPort(Protocol):
    """Resolve one worktree and its canonical origin remote."""

    def resolve_worktree_root(self, path: Path) -> Path:
        """Return the absolute Git worktree root."""
        ...

    def canonical_remote(self, path: Path) -> str:
        """Validate and return the canonical origin name."""
        ...

    def remote_url(self, path: Path, remote: str = "origin") -> str:
        """Return the configured URL for one remote."""
        ...
