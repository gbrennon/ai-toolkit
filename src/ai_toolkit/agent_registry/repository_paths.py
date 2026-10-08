from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RepositoryPaths:
    directory: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "directory", self.directory.expanduser().resolve())

    @property
    def agent_config(self) -> Path:
        return self.directory / "AGENT.md"

    @property
    def metadata(self) -> Path:
        return self.directory / "metadata.json"

    @property
    def skills(self) -> Path:
        return self.directory / "skills.json"

    @property
    def hooks(self) -> Path:
        return self.directory / "hooks.json"

    @property
    def audit_dir(self) -> Path:
        return self.directory / "audit"

    @property
    def changes_audit(self) -> Path:
        return self.audit_dir / "changes.ndjson"
