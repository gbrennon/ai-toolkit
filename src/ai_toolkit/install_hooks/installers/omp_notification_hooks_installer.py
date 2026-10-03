import sys
from pathlib import Path
from typing import Self

OMP_NOTIFICATION_HOOK_PATH: Path = (
    Path.home() / ".omp" / "agent" / "hooks" / "post" / "ai-toolkit-notify.ts"
)
OMP_NOTIFICATION_HOOK_CONTENT: str = """import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const NOTIFY_TITLE: string = "omp agent";
const TMUX_STATE_FORMAT: string = "#{session_name}|#{client_session}|#{window_index}|#{window_active}";

type TaskStatus = "success" | "failure";

interface TmuxWindowState {
  sessionName: string;
  clientSession: string;
  windowIndex: string;
  windowActive: boolean;
}

interface RunMessage {
  role?: string;
  stopReason?: string;
  isError?: boolean;
}

function latestMessageWithRole(
  messages: readonly RunMessage[],
  role: string,
): RunMessage | undefined {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.role === role) return message;
  }
  return undefined;
}

function runStatus(messages: readonly RunMessage[]): TaskStatus {
  const assistant = latestMessageWithRole(messages, "assistant");
  if (assistant?.stopReason === "error" || assistant?.stopReason === "aborted") {
    return "failure";
  }
  const toolResult = latestMessageWithRole(messages, "toolResult");
  if (toolResult?.isError === true) return "failure";
  return "success";
}

async function tmuxWindowState(
  pi: ExtensionAPI,
  cwd: string,
): Promise<TmuxWindowState | null> {
  if (!process.env.TMUX) return null;
  try {
    const result = await pi.exec(
      "tmux",
      ["display-message", "-p", TMUX_STATE_FORMAT],
      { cwd },
    );
    if (result.code !== 0) return null;
    const [sessionName, clientSession, windowIndex, windowActive] =
      result.stdout.trim().split("|");
    return {
      sessionName: sessionName ?? "",
      clientSession: clientSession ?? "",
      windowIndex: windowIndex ?? "",
      windowActive: windowActive === "1",
    };
  } catch {
    return null;
  }
}

function userIsViewingWindow(state: TmuxWindowState | null): boolean {
  if (state === null) return false;
  return state.clientSession !== "" && state.windowActive;
}

function attentionLocation(state: TmuxWindowState | null, cwd: string): string {
  if (state !== null && state.sessionName) {
    return `${cwd} (tmux ${state.sessionName}:${state.windowIndex})`;
  }
  return cwd;
}

async function notifyAttention(
  pi: ExtensionAPI,
  cwd: string,
  reason: string,
): Promise<void> {
  try {
    const state = await tmuxWindowState(pi, cwd);
    if (userIsViewingWindow(state)) return;
    const message = `omp: ${reason} in ${attentionLocation(state, cwd)}`;
    await pi.exec("notify-send", [NOTIFY_TITLE, message], { cwd });
  } catch {
  }
}

export default function notifyHook(pi: ExtensionAPI): void {
  let status: TaskStatus = "success";

  pi.on("ui_prompt_start", async (_event, ctx) => {
    if (!ctx.hasUI) return;
    await notifyAttention(pi, ctx.cwd, "input needed");
  });

  pi.on("agent_start", (_event) => {
    status = "success";
  });

  pi.on("agent_end", (event) => {
    status = runStatus(event.messages as readonly RunMessage[]);
  });

  pi.on("agent_settled", async (_event, ctx) => {
    if (!ctx.hasUI) return;
    const reason = status === "success" ? "task complete" : "task failed";
    await notifyAttention(pi, ctx.cwd, reason);
  });
}"""


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
