from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import subprocess

from .errors import GitResolutionError, MissingOriginError
from .git_invocation import GitInvocation
from .git_result import GitResult
from .git_runner import GitRunner


def _run_subprocess(invocation: GitInvocation) -> GitResult:
    return subprocess.run(
        ["git", *invocation.args],
        cwd=invocation.cwd,
        check=invocation.check,
        capture_output=invocation.capture_output,
        text=invocation.text,
        shell=invocation.shell,
    )


@dataclass(frozen=True, slots=True, init=False)
class GitResolver:
    """Resolve Git worktree roots and the fixed canonical origin remote."""

    _runner: GitRunner

    def __init__(self, runner: GitRunner | None = None) -> None:
        selected = _run_subprocess if runner is None else runner
        object.__setattr__(self, "_runner", selected)

    def resolve_worktree_root(self, path: Path | str) -> Path:
        """Return Git's absolute worktree root for a nested input path."""
        cwd = self._resolve_cwd(path)
        result = self._run(("rev-parse", "--show-toplevel"), cwd)
        value = self._output(result, "rev-parse --show-toplevel", cwd)
        root = Path(value)
        if not root.is_absolute():
            raise GitResolutionError(
                f"git returned a non-absolute worktree root: {value!r}",
                operation="git rev-parse --show-toplevel",
                path=cwd,
            )
        return root.resolve()

    def canonical_remote(self, path: Path | str) -> str:
        """Validate and return the canonical remote name, always `origin`."""
        cwd = self._resolve_cwd(path)
        self._remote_output(cwd, "origin")
        return "origin"

    def remote_url(self, path: Path | str, remote: str = "origin") -> str:
        """Return a configured remote URL without substituting another remote."""
        cwd = self._resolve_cwd(path)
        return self._remote_output(cwd, remote)

    def _resolve_cwd(self, path: Path | str) -> Path:
        try:
            return Path(path).expanduser().resolve()
        except OSError as error:
            raise GitResolutionError(
                f"cannot resolve Git working directory: {error}",
                operation="resolve cwd",
                path=Path(path),
            ) from error

    def _run(self, args: Sequence[str], cwd: Path) -> GitResult:
        try:
            return self._runner(GitInvocation(args=args, cwd=cwd))
        except OSError as error:
            operation = f"git {' '.join(args)}"
            raise GitResolutionError(str(error), operation=operation, path=cwd) from error

    def _output(self, result: GitResult, operation: str, cwd: Path) -> str:
        if result.returncode != 0:
            detail = result.stderr or "Git returned a non-zero status"
            raise GitResolutionError(f"{operation}: {detail}", operation=operation, path=cwd)
        stdout = result.stdout or ""
        if not stdout.strip():
            raise GitResolutionError(
                "Git returned an empty result",
                operation=operation,
                path=cwd,
            )
        return stdout.strip()

    def _remote_output(self, cwd: Path, remote: str) -> str:
        self._validate_remote_name(cwd, remote)
        operation = f"git remote get-url {remote}"
        result = self._run(("remote", "get-url", remote), cwd)
        if result.returncode != 0 and remote == "origin":
            raise MissingOriginError(cwd)
        return self._output(result, operation, cwd)

    def _validate_remote_name(self, cwd: Path, remote: str) -> None:
        if not remote or remote.strip() != remote or any(char.isspace() for char in remote):
            self._raise_invalid_remote(cwd, remote)

    def _raise_invalid_remote(self, cwd: Path, remote: str) -> None:
        raise GitResolutionError(
            f"invalid remote name: {remote!r}",
            operation="git remote get-url",
            path=cwd,
        )
