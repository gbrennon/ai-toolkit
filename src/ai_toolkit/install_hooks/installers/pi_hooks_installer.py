import json
import shutil
import sys
from pathlib import Path
from typing import Any, Self

PI_SETTINGS: Path = Path.home() / ".pi" / "agent" / "settings.json"
PI_NOTIFICATION_EXTENSION_PATH: Path = (
    Path.home() / ".pi" / "agent" / "extensions" / "ai-toolkit-notify.ts"
)
HOOK_PACKAGE: str = "@hsingjui/pi-hooks"
HOOK_CMD: str = "check-modified-code-quality"
HOOK_MATCHER: str = "write|edit"
LEGACY_NOTIFICATION_CMD: str = (
    "tmux_session=''; "
    'if [ -n "${TMUX:-}" ]; then '
    "tmux_state=$(tmux display-message -p "
    "'#{session_name}|#{client_session}|#{window_active}'); "
    "tmux_session=${tmux_state%%|*}; "
    "tmux_visibility=${tmux_state#*|}; "
    "client_session=${tmux_visibility%%|*}; "
    "active=${tmux_visibility##*|}; "
    'if [ -n "$client_session" ] && [ "$active" = \'1\' ]; then exit 0; fi; '
    "fi; "
    'message="pi: attention needed in $PWD"; '
    'if [ -n "$tmux_session" ]; then '
    'message="$message (tmux $tmux_session)"; '
    "fi; "
    "notify-send 'pi agent' \"$message\""
)
PI_NOTIFICATION_EXTENSION_CONTENT: str = """import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

type NotificationEvent = "question" | "complete" | "error";

type AgentOutcome = "completed" | "aborted" | "error";

async function notify(
  pi: ExtensionAPI,
  event: NotificationEvent,
  cwd: string,
  message: string,
): Promise<void> {
  try {
    await pi.exec(
      "agent-notify",
      ["pi", event, "--cwd", cwd, "--message", message],
      { cwd },
    );
  } catch {
    return;
  }
}

export default function notifyHook(pi: ExtensionAPI): void {
  let outcome: AgentOutcome = "completed";

  pi.on("ui_prompt_start", async (_event, ctx) => {
    await notify(pi, "question", ctx.cwd, "input needed");
  });

  pi.on("agent_start", () => {
    outcome = "completed";
  });

  pi.on("agent_before_settle", (event) => {
    outcome = event.outcome;
  });

  pi.on("agent_settled", async (_event, ctx) => {
    const event: NotificationEvent = outcome === "completed" ? "complete" : "error";
    const message = event === "complete" ? "task complete" : "task failed";
    await notify(pi, event, ctx.cwd, message);
  });
}"""

CODE_EXTENSIONS: tuple[str, ...] = (
    "py",
    "rs",
    "go",
    "ts",
    "tsx",
    "js",
    "jsx",
    "java",
    "kt",
    "swift",
    "cs",
    "c",
    "h",
    "cc",
    "cpp",
    "hpp",
    "cxx",
    "rb",
    "php",
    "scala",
    "lua",
    "sh",
    "md",
    "markdown",
)


class PiHooksInstaller:
    """Install Pi quality hooks and a native lifecycle notification extension."""

    def __init__(self, settings_path: Path, extension_path: Path) -> None:
        self._settings_path = settings_path
        self._extension_path = extension_path

    @classmethod
    def create(
        cls,
        settings_path: Path | None = None,
        extension_path: Path | None = None,
    ) -> Self:
        """Return an installer targeting Pi settings and global extensions."""
        resolved_settings = settings_path if settings_path is not None else PI_SETTINGS
        resolved_extension = extension_path
        if resolved_extension is None:
            resolved_extension = (
                PI_NOTIFICATION_EXTENSION_PATH
                if settings_path is None
                else resolved_settings.parent / "extensions" / "ai-toolkit-notify.ts"
            )
        return cls(resolved_settings, resolved_extension)

    def _build_hook_group(self) -> dict[str, Any]:
        """Build the PostToolUse hook group with conditions per code extension."""
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
        """Load settings from file or return empty data if the file is absent."""
        if self._settings_path.is_file():
            return json.loads(self._settings_path.read_text(encoding="utf-8"))
        return {}

    def _ensure_package_in_list(self, data: dict[str, Any]) -> None:
        """Ensure the quality hook package is present exactly once."""
        packages = data.setdefault("packages", [])
        if HOOK_PACKAGE not in packages:
            packages.append(HOOK_PACKAGE)

    def _remaining_stop_groups(self, stop_groups: list[object]) -> list[object]:
        return [
            group
            for group in stop_groups
            if not self._is_legacy_notification_group(group)
        ]

    def _remove_legacy_notification(self, data: dict[str, Any]) -> None:
        """Remove only the legacy notification group from Pi Stop hooks."""
        hooks = data.get("hooks")
        if not isinstance(hooks, dict):
            return
        stop_groups = hooks.get("Stop")
        if not isinstance(stop_groups, list):
            return
        remaining_groups = self._remaining_stop_groups(stop_groups)
        if remaining_groups:
            hooks["Stop"] = remaining_groups
        else:
            hooks.pop("Stop", None)

    @staticmethod
    def _is_legacy_notification_group(group: object) -> bool:
        if not isinstance(group, dict):
            return False
        group_hooks = group.get("hooks")
        if not isinstance(group_hooks, list) or len(group_hooks) != 1:
            return False
        hook = group_hooks[0]
        return isinstance(hook, dict) and hook.get("command") == LEGACY_NOTIFICATION_CMD

    def _write_settings(self, data: dict[str, Any]) -> None:
        """Write Pi settings, creating the settings directory when necessary."""
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def _write_notification_extension(self) -> None:
        """Write the native Pi lifecycle extension."""
        self._extension_path.parent.mkdir(parents=True, exist_ok=True)
        self._extension_path.write_text(
            PI_NOTIFICATION_EXTENSION_CONTENT,
            encoding="utf-8",
        )

    def install(self) -> bool:
        """Install quality hooks, migrate legacy notifications, and write the extension."""
        try:
            data = self._load_or_init_settings()
            hooks = data.setdefault("hooks", {})
            hooks["PostToolUse"] = [self._build_hook_group()]
            self._remove_legacy_notification(data)
            self._ensure_package_in_list(data)
            self._write_notification_extension()
            self._write_settings(data)
            print(
                f"  Pi: quality hooks and notification extension installed in "
                f"{self._settings_path}"
            )
            return True
        except Exception as error:
            print(f"Pi hook failed: {error}", file=sys.stderr)
            return False


def install_hooks() -> bool:
    """Copy the package's PR-opened hook into the local hooks directory."""
    hooks_dir = Path(".hooks")
    source_file = Path(__file__).resolve().parents[2] / "hooks" / "pr_opened_hook.py"
    destination = hooks_dir / source_file.name

    try:
        hooks_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)
        print(f"[HOOK] Installed {destination}")
        return True
    except (OSError, shutil.Error) as error:
        print(f"[HOOK] Failed to install hook: {error}")
        return False
