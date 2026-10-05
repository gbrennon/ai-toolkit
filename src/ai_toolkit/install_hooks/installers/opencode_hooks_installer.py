import sys
from pathlib import Path
from typing import Self

OPENCODE_HOOK_PATH: Path = (
    Path.home() / ".config" / "opencode" / "plugins" / "ai-toolkit-quality.ts"
)
OPENCODE_HOOK_CONTENT: str = '''const CODE_EXTENSIONS: Set<string> = new Set([
  "py", "rs", "go", "ts", "tsx", "js", "jsx", "java", "kt", "swift",
  "cs", "c", "h", "cc", "cpp", "hpp", "cxx", "rb", "php", "scala", "lua", "sh",
  "md", "markdown",
]);
const EDIT_TOOLS: Set<string> = new Set(["write", "edit"]);

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
  const breakerProcess = Bun.spawn([
    "ai-toolkit-hook-circuit-breaker", action, "--session", session,
    "--cwd", cwd, "--path", path,
  ], { cwd, stdout: "pipe", stderr: "pipe" });
  const code = await breakerProcess.exited;
  const stderr = await new Response(breakerProcess.stderr).text();
  return { code, stderr };
}

export const AiToolkitQuality = async ({ directory }) => ({
  "tool.execute.after": async (input, output) => {
    const toolName = input.tool.toLowerCase();
    if (!EDIT_TOOLS.has(toolName) && toolName !== "read") return;
    const path = String(input.args?.filePath ?? input.args?.path ?? "");
    if (!path || !isSourceCodePath(path)) return;

    const session = String(input.sessionID ?? input.sessionId ?? directory);
    if (toolName === "read") {
      await runBreaker("reset", path, directory, session);
      return;
    }

    const before = await runBreaker("before", path, directory, session);
    if (before.code !== 0) {
      output.output += `\\n${before.stderr}`;
      return;
    }

    const process = Bun.spawn(["check-code-quality", path], {
      cwd: directory,
      stdout: "pipe",
      stderr: "pipe",
    });
    const status = await process.exited;
    if (status === 0) {
      await runBreaker("success", path, directory, session);
      return;
    }

    const stderr = await new Response(process.stderr).text();
    const stdout = await new Response(process.stdout).text();
    const failure = await runBreaker("failure", path, directory, session);
    output.output += `\\nCode quality check failed:\\n${stderr || stdout}${failure.stderr ? `\\n${failure.stderr}` : ""}`;
  },
});
'''


class OpenCodeHooksInstaller:
    """Install the OpenCode post-tool quality plugin."""

    def __init__(self, plugin_path: Path) -> None:
        self._plugin_path = plugin_path

    @property
    def plugin_path(self) -> Path:
        """Return the path where the OpenCode plugin is installed."""
        return self._plugin_path

    @classmethod
    def create(cls, plugin_path: Path | None = None) -> Self:
        """Return an installer targeting the default OpenCode plugin path."""
        return cls(plugin_path if plugin_path is not None else OPENCODE_HOOK_PATH)

    def install(self) -> bool:
        """Write the OpenCode plugin, creating its parent directories as needed."""
        try:
            self._plugin_path.parent.mkdir(parents=True, exist_ok=True)
            self._plugin_path.write_text(OPENCODE_HOOK_CONTENT, encoding="utf-8")
            print(f"  OpenCode: quality hook installed in {self._plugin_path}")
            return True
        except OSError as error:
            print(f"OpenCode hook failed: {error}", file=sys.stderr)
            return False
