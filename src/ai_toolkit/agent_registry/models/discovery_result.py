from dataclasses import dataclass
from pathlib import Path

from .validation_report import ValidationReport


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Immutable result for one global registry discovery operation."""

    repository_id: str
    agent_config_path: Path
    validation_report: ValidationReport

    def __post_init__(self) -> None:
        if not self.repository_id.strip():
            raise ValueError("repository_id must be nonempty")
        resolved = self.agent_config_path.expanduser().resolve()
        if (
            not self.agent_config_path.is_absolute()
            or self.agent_config_path != resolved
        ):
            raise ValueError("agent_config_path must be an absolute resolved path")
