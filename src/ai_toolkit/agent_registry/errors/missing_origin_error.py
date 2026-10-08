from pathlib import Path

from .git_resolution_error import GitResolutionError


class MissingOriginError(GitResolutionError):
    """Report that the canonical origin remote is unavailable."""

    def __init__(self, path: Path) -> None:
        super().__init__(
            "canonical remote 'origin' is not configured; another remote will not be substituted",
            operation="git remote get-url origin",
            path=path,
        )
