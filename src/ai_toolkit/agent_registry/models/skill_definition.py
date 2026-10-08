from dataclasses import dataclass
from pathlib import Path

from ._json import JsonValue


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Resolved global skill metadata and source path."""

    id: str
    version: str
    path: Path
    triggers: tuple[str, ...] = ()

    def to_json(self) -> dict[str, JsonValue]:
        """Return the strict skill reference representation."""
        result: dict[str, JsonValue] = {"id": self.id, "version": self.version}
        if self.triggers:
            result["triggers"] = list(self.triggers)
        return result
