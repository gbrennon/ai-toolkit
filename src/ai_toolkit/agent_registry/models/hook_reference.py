from dataclasses import dataclass

from ._json import JsonValue


@dataclass(frozen=True, slots=True)
class HookReference:
    """Registry-local reference to one globally installed hook."""

    id: str
    version: str

    def to_json(self) -> dict[str, JsonValue]:
        """Return the strict hooks manifest entry."""
        return {"id": self.id, "version": self.version}
