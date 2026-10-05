from pathlib import Path
from typing import Any, Dict, List

from ai_toolkit.install_mcp_servers.models.mcp_server_def import McpServerDef
from ai_toolkit.install_mcp_servers.config_dependencies import ConfigDependencies
from ai_toolkit.install_mcp_servers.parsing.load_mcp_json import load_mcp_json


class ConfigManager:
    """Facade coordinating config discovery, loading, overrides, and parsing.

    Construct with ``ConfigManager()`` for defaults, or inject a
    ``ConfigDependencies`` instance for testability.
    """

    def __init__(
        self,
        platform: str = "linux",
        deps: ConfigDependencies | None = None,
    ) -> None:
        self.platform = platform
        d = deps or ConfigDependencies()
        self._config_paths = d.config_paths
        self._config_loader = d.config_loader
        self._env_override_applier = d.env_override_applier
        self._server_config_parser = d.server_config_parser

    def get_standard_config_paths(self) -> List[Path]:
        return self._config_paths.get_standard_config_paths(self.platform)

    def find_config_files(self) -> List[Path]:
        standard_paths = self.get_standard_config_paths()
        return [path for path in standard_paths if path.exists()]

    def load_config_hierarchy(self) -> Dict[str, Any]:
        config_files = self.find_config_files()
        assert self._config_loader is not None
        merged_config = self._config_loader.load_config_hierarchy(config_files)
        merged_config = self._apply_env_overrides(merged_config)
        return merged_config

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return self._env_override_applier.apply_env_overrides(config)

    def get_servers_from_config(self) -> List[McpServerDef]:
        config = self.load_config_hierarchy()
        return self._server_config_parser.get_servers_from_config(config)

    def load_from_file(self, file_path: Path) -> List[McpServerDef]:
        return load_mcp_json(file_path)
