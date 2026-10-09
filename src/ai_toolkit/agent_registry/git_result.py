from typing import Protocol


class GitResult(Protocol):
    """Expose the subprocess fields consumed by Git resolution."""

    returncode: int
    stdout: str | None
    stderr: str | None
