import json
import shutil
import sys
from pathlib import Path
from typing import Any, Self

PI_SETTINGS: Path = Path.home() / ".pi" / "agent" / "settings.json"
PI_QUALITY_EXTENSION_PATH: Path = (
    Path.home() / ".pi" / "agent" / "extensions" / "ai-toolkit-quality.ts"
)
PI_NOTIFICATION_EXTENSION_PATH: Path = (
    Path.home() / ".pi" / "agent" / "extensions" / "ai-toolkit-notify.ts"
)
HOOK_PACKAGE: str = "@hsingjui/pi-hooks"
NPM_HOOK_PACKAGE: str = "npm:@hsingjui/pi-hooks"
LEGACY_QUALITY_CMD: str = "check-modified-code-quality"
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
PI_QUALITY_EXTENSION_CONTENT: str = """import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const CODE_EXTENSIONS: Readonly<Record<string, true>> = {
  py: true, rs: true, go: true, ts: true, tsx: true, js: true, jsx: true,
  java: true, kt: true, swift: true, cs: true, c: true, h: true, cc: true,
  cpp: true, hpp: true, cxx: true, rb: true, php: true, scala: true,
  lua: true, sh: true, md: true, markdown: true,
};
const EDIT_TOOLS: Readonly<Record<string, true>> = { write: true, edit: true };

interface BreakerRecord {
  failures: number;
}

class CircuitBreakerStore {
  private readonly statePath: string;
  private readonly threshold: number;

  public constructor() {
    const customPath = process.env.AI_TOOLKIT_CIRCUIT_BREAKER_STATE || "";
    const stateBase =
      process.env.XDG_STATE_HOME || join(homedir(), ".local", "state");
    this.statePath =
      customPath || join(stateBase, "ai-toolkit", "hook-circuit-breaker.json");
    const rawLimit = process.env.AI_TOOLKIT_CIRCUIT_BREAKER_THRESHOLD || "3";
    const parsed = Number.parseInt(rawLimit, 10);
    this.threshold = Number.isNaN(parsed) || parsed < 1 ? 3 : parsed;
  }

  public isOpen(session: string, cwd: string, path: string): boolean {
    const entry = this.readAll()[this.key(session, cwd, path)];
    return Boolean(entry && entry.failures >= this.threshold);
  }

  public reset(session: string, cwd: string, path: string): void {
    const data = this.readAll();
    const targetKey = this.key(session, cwd, path);
    if (!(targetKey in data)) return;
    delete data[targetKey];
    this.writeAll(data);
  }

  public recordFailure(session: string, cwd: string, path: string): string {
    const data = this.readAll();
    const targetKey = this.key(session, cwd, path);
    const current = data[targetKey];
    const nextFailures = current ? current.failures + 1 : 1;
    data[targetKey] = { failures: nextFailures };
    this.writeAll(data);
    return nextFailures >= this.threshold
      ? this.formatOpenPayload(session, cwd, path, nextFailures)
      : "";
  }

  public formatOpenPayload(
    session: string,
    cwd: string,
    path: string,
    failures: number = this.threshold,
  ): string {
    return JSON.stringify({
      type: "circuit_breaker_open",
      status: "terminal",
      session,
      cwd,
      path: resolve(cwd, path),
      failures,
      action: "read_file_again_or_request_help",
    });
  }

  private key(session: string, cwd: string, path: string): string {
    return `${session}::${resolve(cwd, path)}`;
  }

  private readAll(): Record<string, BreakerRecord> {
    if (!existsSync(this.statePath)) return {};
    try {
      const parsed = JSON.parse(readFileSync(this.statePath, "utf-8"));
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  private writeAll(data: Record<string, BreakerRecord>): void {
    try {
      mkdirSync(dirname(this.statePath), { recursive: true });
      writeFileSync(this.statePath, JSON.stringify(data, null, 2), "utf-8");
    } catch {
      return;
    }
  }
}

function isSourceCodePath(path: string): boolean {
  const dotIndex = path.lastIndexOf(".");
  if (dotIndex <= 0) return false;
  const extension = path.slice(dotIndex + 1).toLowerCase();
  return Boolean(CODE_EXTENSIONS[extension]);
}

export default function qualityHook(pi: ExtensionAPI): void {
  const breaker = new CircuitBreakerStore();

  pi.on("tool_result", async (event, ctx) => {
    if (event.isError) return;
    const toolName = event.toolName.toLowerCase();
    if (!EDIT_TOOLS[toolName] && toolName !== "read") return;
    const path = String(event.input.path || event.input.filePath || "");
    if (!path || !isSourceCodePath(path)) return;

    const session = String((ctx as { sessionId?: string }).sessionId || ctx.cwd);
    if (toolName === "read") {
      breaker.reset(session, ctx.cwd, path);
      return;
    }

    if (breaker.isOpen(session, ctx.cwd, path)) {
      const openMessage = breaker.formatOpenPayload(session, ctx.cwd, path);
      return {
        content: [...event.content, { type: "text", text: openMessage }],
      };
    }

    const result = await pi.exec("check-code-quality", [path], { cwd: ctx.cwd });
    if (result.code === 0) {
      breaker.reset(session, ctx.cwd, path);
      return;
    }

    const terminal = breaker.recordFailure(session, ctx.cwd, path);
    const output = result.stderr || result.stdout;
    const suffix = terminal ? `\\n${terminal}` : "";
    return {
      content: [
        ...event.content,
        { type: "text", text: `Code quality check failed:\\n${output}${suffix}` },
      ],
    };
  });
}
"""
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


class PiHooksInstaller:
    """Install native TypeScript Pi quality and lifecycle notification extensions."""

    def __init__(
        self,
        settings_path: Path,
        extension_path: Path,
        quality_extension_path: Path | None = None,
    ) -> None:
        self._settings_path = settings_path
        self._extension_path = extension_path
        self._quality_extension_path = (
            quality_extension_path
            if quality_extension_path is not None
            else extension_path.parent / "ai-toolkit-quality.ts"
        )

    @classmethod
    def create(
        cls,
        settings_path: Path | None = None,
        extension_path: Path | None = None,
        quality_extension_path: Path | None = None,
    ) -> Self:
        """Return an installer targeting Pi settings and global extensions."""
        resolved_settings = settings_path if settings_path is not None else PI_SETTINGS
        resolved_notify = cls._resolve_notify_path(settings_path, extension_path)
        resolved_quality = cls._resolve_quality_path(
            settings_path,
            resolved_notify,
            quality_extension_path,
        )
        return cls(resolved_settings, resolved_notify, resolved_quality)

    @staticmethod
    def _resolve_notify_path(
        settings_path: Path | None,
        extension_path: Path | None,
    ) -> Path:
        if extension_path is not None:
            return extension_path
        if settings_path is None:
            return PI_NOTIFICATION_EXTENSION_PATH
        return settings_path.parent / "extensions" / "ai-toolkit-notify.ts"

    @staticmethod
    def _resolve_quality_path(
        settings_path: Path | None,
        notify_path: Path,
        quality_extension_path: Path | None,
    ) -> Path:
        if quality_extension_path is not None:
            return quality_extension_path
        if settings_path is None and notify_path == PI_NOTIFICATION_EXTENSION_PATH:
            return PI_QUALITY_EXTENSION_PATH
        return notify_path.parent / "ai-toolkit-quality.ts"

    def _load_or_init_settings(self) -> dict[str, Any]:
        """Load settings from file or return empty data if the file is absent."""
        if self._settings_path.is_file():
            return json.loads(self._settings_path.read_text(encoding="utf-8"))
        return {}

    def _remove_legacy_packages(self, data: dict[str, Any]) -> None:
        """Remove legacy @hsingjui/pi-hooks entries from Pi packages."""
        packages = data.get("packages")
        if not isinstance(packages, list):
            return
        remaining = [
            pkg
            for pkg in packages
            if pkg not in (HOOK_PACKAGE, NPM_HOOK_PACKAGE)
        ]
        if remaining:
            data["packages"] = remaining
        else:
            data.pop("packages", None)

    def _remove_legacy_hooks(self, data: dict[str, Any]) -> None:
        """Remove legacy shell quality and notification hooks from Pi settings."""
        hooks = data.get("hooks")
        if not isinstance(hooks, dict):
            return
        self._prune_hook_section(hooks, "PostToolUse", LEGACY_QUALITY_CMD)
        self._prune_hook_section(hooks, "Stop", LEGACY_NOTIFICATION_CMD)
        if not hooks:
            data.pop("hooks", None)

    def _prune_hook_section(
        self,
        hooks: dict[str, Any],
        section: str,
        legacy_command: str,
    ) -> None:
        groups = hooks.get(section)
        if not isinstance(groups, list):
            return
        remaining = [
            group
            for group in groups
            if not self._matches_legacy_command(group, legacy_command)
        ]
        if remaining:
            hooks[section] = remaining
        else:
            hooks.pop(section, None)

    @classmethod
    def _matches_legacy_command(cls, group: object, legacy_command: str) -> bool:
        commands = cls._extract_group_commands(group)
        return bool(commands) and all(cmd == legacy_command for cmd in commands)

    @staticmethod
    def _extract_group_commands(group: object) -> list[object]:
        if not isinstance(group, dict):
            return []
        group_hooks = group.get("hooks")
        if not isinstance(group_hooks, list):
            return []
        return [
            hook.get("command") if isinstance(hook, dict) else None
            for hook in group_hooks
        ]

    def _write_settings(self, data: dict[str, Any]) -> None:
        """Write Pi settings, creating the settings directory when necessary."""
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def _write_extensions(self) -> None:
        """Write the native Pi quality and lifecycle notification extensions."""
        self._quality_extension_path.parent.mkdir(parents=True, exist_ok=True)
        self._quality_extension_path.write_text(
            PI_QUALITY_EXTENSION_CONTENT,
            encoding="utf-8",
        )
        self._extension_path.parent.mkdir(parents=True, exist_ok=True)
        self._extension_path.write_text(
            PI_NOTIFICATION_EXTENSION_CONTENT,
            encoding="utf-8",
        )

    def install(self) -> bool:
        """Migrate legacy shell hooks and write native Pi TypeScript extensions."""
        try:
            data = self._load_or_init_settings()
            self._remove_legacy_hooks(data)
            self._remove_legacy_packages(data)
            self._write_extensions()
            self._write_settings(data)
            print(
                f"  Pi: native quality and notification extensions installed in "
                f"{self._extension_path.parent}"
            )
            return True
        except Exception as error:
            print(f"Pi hook failed: {error}", file=sys.stderr)
            return False

    @staticmethod
    def install_repository_hook() -> bool:
        """Copy the package's PR-opened hook into the local hooks directory."""
        hooks_dir = Path(".hooks")
        source_file = (
            Path(__file__).resolve().parents[2] / "hooks" / "pr_opened_hook.py"
        )
        destination = hooks_dir / source_file.name
        try:
            hooks_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination)
            print(f"[HOOK] Installed {destination}")
            return True
        except (OSError, shutil.Error) as error:
            print(f"[HOOK] Failed to install hook: {error}")
            return False


install_hooks = PiHooksInstaller.install_repository_hook
