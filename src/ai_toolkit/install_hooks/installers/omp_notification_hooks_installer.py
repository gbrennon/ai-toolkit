import sys
from pathlib import Path
from typing import Self

OMP_NOTIFICATION_HOOK_PATH: Path = (
    Path.home() / ".omp" / "agent" / "hooks" / "post" / "ai-toolkit-notify.ts"
)
OMP_NOTIFICATION_HOOK_CONTENT: str = '''import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";

const NOTIFY_TITLE: string = "omp agent";
const TMUX_STATE_FORMAT: string = "#{session_name}|#{client_session}|#{window_active}";

interface TmuxWindowState {
  sessionName: string;
  clientSession: string;
  windowActive: boolean;
}

interface AttentionContext {
  hasQueuedMessages?: () => boolean;
  isIdle?: () => boolean;
}

function taskIsComplete(context: AttentionContext): boolean {
  if (typeof context.hasQueuedMessages === "function") {
    return !context.hasQueuedMessages();
  }
  if (typeof context.isIdle === "function") return context.isIdle();
  return false;
}

async function tmuxWindowState(pi: HookAPI, cwd: string): Promise<TmuxWindowState | null> {
  if (!process.env.TMUX) return null;
  const result = await pi.exec("tmux", ["display-message", "-p", TMUX_STATE_FORMAT], { cwd });
  if (result.code !== 0) return null;
  const [sessionName, clientSession, windowActive] = result.stdout.trim().split("|");
  return {
    sessionName: sessionName ?? "",
    clientSession: clientSession ?? "",
    windowActive: windowActive === "1",
  };
}

function userIsViewingWindow(state: TmuxWindowState | null): boolean {
  if (state === null) return false;
  return state.clientSession !== "" && state.windowActive;
}

function attentionLocation(state: TmuxWindowState | null, cwd: string): string {
  if (state !== null && state.sessionName) return `${cwd} (tmux ${state.sessionName})`;
  return cwd;
}

async function notifyAttention(pi: HookAPI, cwd: string, reason: string): Promise<void> {
  const state = await tmuxWindowState(pi, cwd);
  if (userIsViewingWindow(state)) return;
  const message = `omp: ${reason} in ${attentionLocation(state, cwd)}`;
  await pi.exec("notify-send", [NOTIFY_TITLE, message], { cwd });
}

export default function notifyHook(pi: HookAPI): void {
  pi.on("turn_end", async (_event, ctx) => {
    if (!ctx.hasUI) return;
    const attentionContext: AttentionContext = ctx;
    if (!taskIsComplete(attentionContext)) return;
    await notifyAttention(pi, ctx.cwd, "task complete");
  });

  pi.on("tool_call", async (event, ctx) => {
    if (!ctx.hasUI) return;
    if (event.toolName !== "ask") return;
    await notifyAttention(pi, ctx.cwd, "input needed");
  });
}'''

class OmpNotificationHooksInstaller:
    """Install the native OMP attention notification hook."""

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