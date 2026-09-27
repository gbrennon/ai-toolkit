import sys
from pathlib import Path
from typing import Self

CLINE_HOOK_PATH: Path = Path.home() / ".cline" / "plugins" / "ai-toolkit-quality.ts"
CLINE_HOOK_CONTENT: str = '''import type { AgentPlugin } from "@cline/core";

const CODE_EXTENSIONS: Set<string> = new Set([
  "py", "rs", "go", "ts", "tsx", "js", "jsx", "java", "kt", "swift",
  "cs", "c", "h", "cc", "cpp", "hpp", "cxx", "rb", "php", "scala", "lua", "sh",
]);

function isSourceCodePath(path: string): boolean {
  const extension = path.split(".").pop()?.toLowerCase() ?? "";
  return CODE_EXTENSIONS.has(extension);
}

async function runBreaker(action: string, path: string): Promise<{ code: number; stderr: string }> {
  const cwd = process.cwd();
  const breakerProcess = Bun.spawn([
    "ai-toolkit-hook-circuit-breaker", action, "--session", cwd,
    "--cwd", cwd, "--path", path,
  ], { cwd, stdout: "pipe", stderr: "pipe" });
  const code = await breakerProcess.exited;
  const stderr = await new Response(breakerProcess.stderr).text();
  return { code, stderr };
}

const plugin: AgentPlugin = {
  name: "ai-toolkit-quality",
  manifest: { capabilities: ["hooks"] },
  hooks: {
    async afterTool({ toolCall, input, result }) {
      const toolName = toolCall.toolName.toLowerCase();
      if (toolName !== "write" && toolName !== "edit" && toolName !== "read") return;
      const path = String(input.path ?? input.filePath ?? "");
      if (!path || !isSourceCodePath(path)) return;

      if (toolName === "read") {
        await runBreaker("reset", path);
        return;
      }

      const before = await runBreaker("before", path);
      if (before.code !== 0) {
        return { ...result, output: `${result.output}\n${before.stderr}` };
      }

      const qualityProcess = Bun.spawn(["check-code-quality", path], {
        cwd: process.cwd(),
        stdout: "pipe",
        stderr: "pipe",
      });
      const status = await qualityProcess.exited;
      if (status === 0) {
        await runBreaker("success", path);
        return;
      }

      const stderr = await new Response(qualityProcess.stderr).text();
      const stdout = await new Response(qualityProcess.stdout).text();
      const failure = await runBreaker("failure", path);
      return {
        ...result,
        output: `${result.output}\\nCode quality check failed:\\n${stderr || stdout}${failure.stderr ? `\\n${failure.stderr}` : ""}`,
      };
    },
  },
};

export default plugin;
'''


class ClineHooksInstaller:
    """Install the Cline post-tool quality plugin."""

    def __init__(self, plugin_path: Path) -> None:
        self._plugin_path = plugin_path

    @property
    def plugin_path(self) -> Path:
        """Return the path where the Cline plugin is installed."""
        return self._plugin_path

    @classmethod
    def create(cls, plugin_path: Path | None = None) -> Self:
        """Return an installer targeting the default Cline plugin path."""
        return cls(plugin_path if plugin_path is not None else CLINE_HOOK_PATH)

    def install(self) -> bool:
        """Write the Cline plugin, creating its parent directories as needed."""
        try:
            self._plugin_path.parent.mkdir(parents=True, exist_ok=True)
            self._plugin_path.write_text(CLINE_HOOK_CONTENT, encoding="utf-8")
            print(f"  Cline: quality hook installed in {self._plugin_path}")
            return True
        except OSError as error:
            print(f"Cline hook failed: {error}", file=sys.stderr)
            return False
