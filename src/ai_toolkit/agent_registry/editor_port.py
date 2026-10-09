from typing import Protocol


class EditorPort(Protocol):
    """Review temporary managed AGENT.md text."""

    def edit(self, content: str) -> str:
        """Return the reviewed AGENT.md content."""
        ...
