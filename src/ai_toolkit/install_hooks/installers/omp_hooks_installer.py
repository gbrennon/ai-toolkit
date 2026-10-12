import sys
from pathlib import Path
from typing import Self

OMP_HOOK_PATH: Path = (
    Path.home() / ".omp" / "agent" / "hooks" / "post" / "ai-toolkit-quality.ts"
)
OMP_HOOK_CONTENT: str = """import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
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
