from dataclasses import dataclass
from datetime import datetime

from ._json import JsonValue, utc_z


@dataclass(frozen=True, slots=True)
class AgentConfigFrontMatter:
    """Strict front matter contract for a managed AGENT.md file."""

    registry_schema: int
    repository_id: str
    git_remote: str
    config_version: int
    last_reviewed: datetime

    def to_json(self) -> dict[str, JsonValue]:
        """Return front matter fields in their external names."""
        return {
            "registrySchema": self.registry_schema,
            "repositoryId": self.repository_id,
            "gitRemote": self.git_remote,
            "configVersion": self.config_version,
            "lastReviewed": utc_z(self.last_reviewed),
        }
