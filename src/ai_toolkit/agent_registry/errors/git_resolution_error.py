from pathlib import Path

from .registry_error import RegistryError


class GitResolutionError(RegistryError):
    """Report a Git command failure with its operation and working path."""

    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        path: Path | None = None,
    ) -> None:
        self.operation = operation
        self.path = path
        context: list[str] = []
        if operation:
            context.append(f"operation={operation}")
        if path is not None:
            context.append(f"path={path}")
        suffix = f" ({', '.join(context)})" if context else ""
        super().__init__(f"{message}{suffix}")
