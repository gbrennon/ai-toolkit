import sys
from pathlib import Path
from typing import Self

OMP_NOTIFICATION_HOOK_PATH: Path = (
    Path.home() / ".omp" / "agent" / "hooks" / "post" / "ai-toolkit-notify.ts"
)
OMP_NOTIFICATION_HOOK_CONTENT: str = """import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

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
      ["omp", event, "--cwd", cwd, "--message", message],
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
        """Write the OMP notification hook, creating parent directories as needed."""
        try:
            self._hook_path.parent.mkdir(parents=True, exist_ok=True)
            self._hook_path.write_text(OMP_NOTIFICATION_HOOK_CONTENT, encoding="utf-8")
            print(f"  OMP: notification hook installed in {self._hook_path}")
            return True
        except OSError as error:
            print(f"OMP notification hook failed: {error}", file=sys.stderr)
            return False
