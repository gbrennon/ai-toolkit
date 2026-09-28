import sys
from pathlib import Path
from typing import Self

OMP_HOOK_PATH: Path = (
    Path.home() / ".omp" / "agent" / "hooks" / "post" / "ai-toolkit-quality.ts"
)
OMP_HOOK_CONTENT: str = '''import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";

const CODE_EXTENSIONS: Set<string> = new Set([
  "py", "rs", "go", "ts", "tsx", "js", "jsx", "java", "kt", "swift",
  "cs", "c", "h", "cc", "cpp", "hpp", "cxx", "rb", "php", "scala", "lua", "sh",
]);
const EDIT_TOOLS: Set<string> = new Set(["write", "edit"]);
const READ_TOOLS: Set<string> = new Set(["read"]);

function isSourceCodePath(path: string): boolean {
  const extension = path.split(".").pop()?.toLowerCase() ?? "";
  return CODE_EXTENSIONS.has(extension);
}

async function runBreaker(
  action: string,
  path: string,
  cwd: string,
  session: string,
): Promise<{ code: number; stderr: string }> {
  const process = Bun.spawn([
    "ai-toolkit-hook-circuit-breaker",
    action,
    "--session",
    session,
    "--cwd",
    cwd,
    "--path",
    path,
  ], { cwd, stdout: "pipe", stderr: "pipe" });
  const code = await process.exited;
  const stderr = await new Response(process.stderr).text();
  return { code, stderr };
}

export default function qualityHook(pi: HookAPI): void {
  pi.on("tool_result", async (event, ctx) => {
    if (event.isError) return;
    const toolName = event.toolName.toLowerCase();
    if (!EDIT_TOOLS.has(toolName) && !READ_TOOLS.has(toolName)) return;
    const path = String(event.input.path ?? "");
    if (!path || !isSourceCodePath(path)) return;

    if (READ_TOOLS.has(toolName)) {
      await runBreaker(
        "reset", path, ctx.cwd,
        String((ctx as { sessionId?: string }).sessionId ?? ctx.cwd),
      );
      return;
    }

    const session = String(
      (ctx as { sessionId?: string }).sessionId ?? ctx.cwd,
    );
    const before = await runBreaker("before", path, ctx.cwd, session);
    if (before.code !== 0) {
      return {
        content: [
          ...event.content,
          { type: "text", text: before.stderr },
        ],
      };
    }

    const result = await pi.exec("check-code-quality", [path], { cwd: ctx.cwd });
    if (result.code === 0) {
      await runBreaker("success", path, ctx.cwd, session);
      return;
    }

    const failure = await runBreaker("failure", path, ctx.cwd, session);
    const output = result.stderr || result.stdout;
    const terminal = failure.stderr ? `\\n${failure.stderr}` : "";
    return {
      content: [
        ...event.content,
        { type: "text", text: `Code quality check failed:\\n${output}${terminal}` },
      ],
    };
  });
}
'''


class OmpHooksInstaller:
    """Install the native OMP post-tool quality hook."""

    def __init__(self, hook_path: Path) -> None:
        self._hook_path = hook_path

    @property
    def hook_path(self) -> Path:
        """Return the path where the native OMP hook is installed."""
        return self._hook_path

    @classmethod
    def create(cls, hook_path: Path | None = None) -> Self:
        """Return an installer targeting the default OMP hook path."""
        return cls(hook_path if hook_path is not None else OMP_HOOK_PATH)

    def install(self) -> bool:
        """Write the OMP hook, creating its parent directories as needed."""
        try:
            self._hook_path.parent.mkdir(parents=True, exist_ok=True)
            self._hook_path.write_text(OMP_HOOK_CONTENT, encoding="utf-8")
            print(f"  OMP: native quality hook installed in {self._hook_path}")
            return True
        except OSError as error:
            print(f"OMP hook failed: {error}", file=sys.stderr)
            return False
