from dataclasses import dataclass
from datetime import datetime

from ._json import JsonValue, utc_z
from .repository_record import RepositoryRecord


@dataclass(frozen=True, slots=True)
class RegistryDocument:
    """Immutable versioned root registry document."""

    schema_version: int
    registry_version: str
    updated_at: datetime
    repositories: tuple[RepositoryRecord, ...]

    def to_json(self) -> dict[str, JsonValue]:
        """Return the strict registry representation."""
        return {
            "schemaVersion": self.schema_version,
            "registryVersion": self.registry_version,
            "updatedAt": utc_z(self.updated_at),
            "repositories": [record.to_json() for record in self.repositories],
        }
