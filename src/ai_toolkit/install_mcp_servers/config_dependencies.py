from __future__ import annotations

from dataclasses import dataclass, field

from ai_toolkit.install_mcp_servers.config_loader import ConfigLoader
from ai_toolkit.install_mcp_servers.config_paths import ConfigPaths
from ai_toolkit.install_mcp_servers.env_override_applier import EnvOverrideApplier
from ai_toolkit.install_mcp_servers.server_config_parser import ServerConfigParser


@dataclass
class ConfigDependencies:
    """Group defaultable collaborators required by configuration management."""

    config_paths: ConfigPaths = field(default_factory=ConfigPaths)
    config_loader: ConfigLoader | None = None
    env_override_applier: EnvOverrideApplier = field(default_factory=EnvOverrideApplier)
    server_config_parser: ServerConfigParser = field(default_factory=ServerConfigParser)

    def __post_init__(self) -> None:
        """Initialize the loader from the configured paths when omitted."""
        if self.config_loader is None:
            self.config_loader = ConfigLoader(self.config_paths)
