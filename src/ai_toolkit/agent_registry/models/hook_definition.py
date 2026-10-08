from dataclasses import dataclass
from pathlib import Path

from ._json import JsonValue


@dataclass(frozen=True, slots=True)
class HookDefinition:
    """Resolved global hook execution contract."""

    id: str
    version: str
    events: tuple[str, ...]
    enabled: bool
    argv: tuple[str, ...]
    timeout: float
    failure_policy: str
    audit: bool
    directory: Path

    def to_json(self) -> dict[str, JsonValue]:
        """Return the strict global hook manifest representation."""
        return {
            "id": self.id,
            "version": self.version,
            "events": list(self.events),
            "enabled": self.enabled,
            "argv": list(self.argv),
            "timeout": self.timeout,
            "failurePolicy": self.failure_policy,
            "audit": self.audit,
        }
