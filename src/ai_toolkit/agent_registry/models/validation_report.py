from dataclasses import dataclass

from ._json import JsonValue
from .validation_issue import ValidationIssue


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Immutable collection of all independent validation issues."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether validation found no issues."""
        return not self.issues

    @property
    def valid(self) -> bool:
        """Return the short-form validity flag."""
        return self.is_valid

    def extend(self, *issues: ValidationIssue) -> "ValidationReport":
        """Return a report containing this report and additional issues."""
        return ValidationReport(self.issues + tuple(issues))

    def to_json(self) -> list[JsonValue]:
        """Return all issues as typed external objects."""
        return [issue.to_json() for issue in self.issues]
