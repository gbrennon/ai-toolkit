from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class AgentArtifactChecker:
    """Reject generated agent state and session artifacts from versioning or edits."""

    def __init__(
        self,
        paths: list[Path],
        rules_path: Path,
        repository_root: Path | None = None,
    ) -> None:
        self._paths = paths
        self._rules_path = rules_path
        self._repository_root_override = repository_root
        self._patterns = self._read_patterns()

    def check(self) -> int:
        """Return zero when no supplied path is an agent-generated artifact."""
        root = self._repository_root()
        failures = [relative for path in self._paths if (relative := self._relative(path, root)) and self._blocked(relative)]
        for relative in failures:
            print(f"{relative}:agent-artifact: generated agent state must not be versioned", file=sys.stderr)
        return int(bool(failures))

    def _read_patterns(self) -> list[str]:
        if not self._rules_path.exists():
            return []
        return [line.strip() for line in self._rules_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _repository_root(self) -> Path:
        if self._repository_root_override is not None:
            return self._repository_root_override.resolve()
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            return Path.cwd().resolve()
        return Path(result.stdout.strip()).resolve()

    def _relative(self, path: Path, root: Path) -> str:
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            return ""

    def _blocked(self, relative: str) -> bool:
        return any(relative == pattern.rstrip("/") or relative.startswith(pattern) for pattern in self._patterns)


def _staged_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line]


def _rules_path() -> Path:
    configured = Path(__import__("os").environ.get("AI_TOOLKIT_RULES_DIR", ""))
    if configured:
        return configured / "agent-artifacts.txt"
    return Path(__file__).resolve().parent.parent / "rules" / "agent-artifacts.txt"


def main(argv: list[str]) -> int:
    """Check explicit paths or staged paths supplied by the command line."""
    paths = _staged_paths() if argv[1:] == ["--staged"] else [Path(value) for value in argv[1:]]
    if not paths:
        return 0
    return AgentArtifactChecker(paths, _rules_path()).check()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
