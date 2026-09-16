import json
import sys
from pathlib import Path
from typing import Any, Self

PI_SETTINGS: Path = Path.home() / ".pi" / "agent" / "settings.json"
HOOK_PACKAGE: str = "@hsingjui/pi-hooks"
HOOK_CMD: str = "check-modified-code-quality"
HOOK_MATCHER: str = "write|edit"

CODE_EXTENSIONS: tuple[str, ...] = (
    "py", "rs", "go", "ts", "tsx", "js", "jsx",
    "java", "kt", "swift", "cs", "c", "h", "cc",
    "cpp", "hpp", "cxx", "rb", "php", "scala", "lua", "sh",
)


class PiHooksInstaller:
    """Install the Pi PostToolUse quality hook and the pi-hooks package."""

    def __init__(self, settings_path: Path) -> None:
        self._settings_path = settings_path

    @classmethod
    def create(cls, settings_path: Path | None = None) -> Self:
        """Return an installer targeting the real Pi settings unless overridden."""
        return cls(settings_path if settings_path is not None else PI_SETTINGS)

    def _build_hook_group(self) -> dict[str, Any]:
        """Build the PostToolUse hook group with if-conditions per code extension."""
        return {
            "matcher": HOOK_MATCHER,
            "hooks": [
                {
                    "type": "command",
                    "if": f"{tool}(*.{extension})",
                    "command": HOOK_CMD,
                }
                for tool in ("Write", "Edit")
                for extension in CODE_EXTENSIONS
            ],
        }

    def _load_or_init_settings(self) -> dict[str, Any]:
        """Load settings from file or return empty dict if file does not exist."""
        if self._settings_path.is_file():
            return json.loads(
                self._settings_path.read_text(encoding="utf-8")
            )
        return {}

    def _ensure_package_in_list(self, data: dict[str, Any]) -> None:
        """Ensure HOOK_PACKAGE is in the packages list without duplicating."""
        packages = data.setdefault("packages", [])
        if HOOK_PACKAGE not in packages:
            packages.append(HOOK_PACKAGE)

    def _write_settings(self, data: dict[str, Any]) -> None:
        """Write settings to file, creating parent directories as needed."""
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def install(self) -> bool:
        try:
            data = self._load_or_init_settings()
            data.setdefault("hooks", {})["PostToolUse"] = [
                self._build_hook_group()
            ]
            self._ensure_package_in_list(data)
            self._write_settings(data)
            print(f"  Pi: PostToolUse hook installed in {self._settings_path}")
            return True
        except Exception as e:
            print(f"Pi hook failed: {e}", file=sys.stderr)
            return False
