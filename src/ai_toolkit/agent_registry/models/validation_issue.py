from dataclasses import dataclass

from ._json import JsonValue


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One independently reported registry validation issue."""

    field: str
    code: str
    message: str

    @property
    def path(self) -> str:
        """Return the field path used by callers that call it a path."""
        return self.field

    def to_json(self) -> dict[str, JsonValue]:
        """Return the issue as a typed external object."""
        return {"field": self.field, "code": self.code, "message": self.message}
