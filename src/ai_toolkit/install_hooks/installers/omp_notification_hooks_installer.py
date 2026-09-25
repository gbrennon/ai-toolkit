import sys
from pathlib import Path
from typing import Self

OMP_NOTIFICATION_HOOK_PATH: Path = (
    Path.home() / ".omp" / "agent" / "hooks" / "post" / "ai-toolkit-notify.ts"
)
OMP_NOTIFICATION_HOOK_CONTENT: str = '''import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";

const NOTIFY_TITLE: string = "omp agent";

async function tmuxSessionName(pi: HookAPI, cwd: string): Promise<string> {
  if (!process.env.TMUX) return "";
  const result = await pi.exec("tmux", ["display-message", "-p", "#{session_name}"], { cwd });
  if (result.code !== 0) return "";
  return result.stdout.trim();
}

export default function notifyHook(pi: HookAPI): void {
  pi.on("turn_end", async (_event, ctx) => {
    const sessionName = await tmuxSessionName(pi, ctx.cwd);
    const location = sessionName ? `${ctx.cwd} (tmux ${sessionName})` : ctx.cwd;
    const message = `omp: attention needed in ${location}`;
    await pi.exec("notify-send", [NOTIFY_TITLE, message], { cwd: ctx.cwd });
  });
}'''

class OmpNotificationHooksInstaller:
    """Install the native OMP turn_end notification hook."""

    def __init__(self, hook_path: Path) -> None:
        self._hook_path = hook_path

    @property
    def hook_path(self) -> Path:
        """Return the path where the native OMP hook is installed."""
        return self._hook_path

    @classmethod
    def create(cls, hook_path: Path | None = None) -> Self:
        """Return an installer targeting the default OMP notification hook path."""
        return cls(hook_path if hook_path is not None else OMP_NOTIFICATION_HOOK_PATH)

    def install(self) -> bool:
        """Write the OMP notification hook, creating its parent directories as needed."""
        try:
            self._hook_path.parent.mkdir(parents=True, exist_ok=True)
            self._hook_path.write_text(OMP_NOTIFICATION_HOOK_CONTENT, encoding="utf-8")
            print(f"  OMP: notification hook installed in {self._hook_path}")
            return True
        except OSError as error:
            print(f"OMP notification hook failed: {error}", file=sys.stderr)
            return False