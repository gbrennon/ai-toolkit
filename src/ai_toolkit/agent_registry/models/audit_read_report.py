from dataclasses import dataclass

from ._json import JsonValue
from .audit_event import AuditEvent
from .validation_issue import ValidationIssue


@dataclass(frozen=True, slots=True)
class AuditReadReport:
    """Parsed audit events together with every malformed-record issue."""

    events: tuple[AuditEvent, ...] = ()
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether every line was a valid audit event."""
        return not self.issues

    def to_json(self) -> dict[str, JsonValue]:
        """Return parsed events and issues as typed external data."""
        return {
            "events": [event.to_json() for event in self.events],
            "issues": [issue.to_json() for issue in self.issues],
        }
