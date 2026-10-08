from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ._json import JsonValue, utc_z
from .repository_status import RepositoryStatus


@dataclass(frozen=True, slots=True)
class RepositoryRecord:
    """Immutable registry metadata for one repository."""

    repository_id: str
    git_remote: str
    local_path: Path
    agent_config_path: Path
    config_sha256: str
    status: RepositoryStatus
    registered_at: datetime
    updated_at: datetime

    @property
    def id(self) -> str:
        """Return the stable registry identifier."""
        return self.repository_id

    def to_json(self) -> dict[str, JsonValue]:
        """Return the strict registry representation."""
        return {
            "id": self.repository_id,
            "gitRemote": self.git_remote,
            "localPath": str(self.local_path),
            "agentConfigPath": str(self.agent_config_path),
            "configSha256": self.config_sha256,
            "status": self.status.value,
            "registeredAt": utc_z(self.registered_at),
            "updatedAt": utc_z(self.updated_at),
        }
