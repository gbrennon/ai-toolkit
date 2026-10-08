from dataclasses import dataclass

from ._json import JsonValue


@dataclass(frozen=True, slots=True)
class SkillReference:
    """Registry-local reference to one globally installed skill."""

    id: str
    version: str
    triggers: tuple[str, ...] = ()

    def to_json(self) -> dict[str, JsonValue]:
        """Return the strict skills manifest entry."""
        result: dict[str, JsonValue] = {"id": self.id, "version": self.version}
        if self.triggers:
            result["triggers"] = list(self.triggers)
        return result
