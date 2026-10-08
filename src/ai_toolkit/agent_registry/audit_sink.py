from typing import Protocol

from .models import AuditEvent


class AuditSink(Protocol):
    """Receive validated audit events from registry operations."""

    def record(self, event: AuditEvent) -> None:
        """Persist or forward one audit event."""
        ...
