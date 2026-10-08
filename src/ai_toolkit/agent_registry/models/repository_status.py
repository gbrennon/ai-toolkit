from enum import StrEnum


class RepositoryStatus(StrEnum):
    """Lifecycle state for a registered repository."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    BLOCKED = "blocked"
