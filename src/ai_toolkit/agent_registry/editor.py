from collections.abc import Mapping
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

from .editor_invocation import EditorInvocation
from .editor_runner import EditorRunner
from .errors import (
    EditorCommandEmptyError,
    EditorExecutionError,
    EditorNotConfiguredError,
    EditorOutputEmptyError,
)


def _run_subprocess(invocation: EditorInvocation) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(invocation.argv),
        env=dict(invocation.environment),
        shell=invocation.shell,
        capture_output=invocation.capture_output,
        text=invocation.text,
        check=invocation.check,
    )


def _select_command(environment: Mapping[str, str]) -> tuple[str, ...]:
    configured = environment.get("VISUAL")
    if configured is None:
        configured = environment.get("EDITOR")
    if configured is None:
        raise EditorNotConfiguredError("set VISUAL or EDITOR before reviewing AGENT.md")
    try:
        command = tuple(shlex.split(configured))
    except ValueError as error:
        raise EditorCommandEmptyError(f"editor command cannot be parsed: {error}") from error
    if not command:
        raise EditorCommandEmptyError("selected editor command is empty")
    return command


def _run_editor(
    runner: EditorRunner, invocation: EditorInvocation
) -> subprocess.CompletedProcess[str]:
    try:
        result = runner(invocation)
    except OSError as error:
        raise EditorExecutionError(f"editor could not be started: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() if result.stderr else "editor returned a nonzero status"
        raise EditorExecutionError(f"editor exited with status {result.returncode}: {detail}")
    return result


class RegistryEditor:
    """Review one temporary managed AGENT.md document with a shell-free editor."""

    def __init__(
        self,
        runner: EditorRunner | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        self._runner = _run_subprocess if runner is None else runner
        self._environment = dict(os.environ if environment is None else environment)

    def edit(self, content: str, temporary_path: Path | None = None) -> str:
        """Write, review, and return temporary UTF-8 AGENT.md content."""
        command = _select_command(self._environment)
        path, remove_after = self._temporary_path(temporary_path)
        try:
            path.write_text(content, encoding="utf-8")
            invocation = EditorInvocation(command + (str(path),), path, self._environment)
            _run_editor(self._runner, invocation)
            result = path.read_text(encoding="utf-8")
            if not result.strip():
                raise EditorOutputEmptyError("editor produced empty AGENT.md content")
            return result
        finally:
            if remove_after:
                path.unlink(missing_ok=True)

    def _temporary_path(self, supplied: Path | None) -> tuple[Path, bool]:
        if supplied is not None:
            return supplied.expanduser().resolve(), False
        descriptor, name = tempfile.mkstemp(prefix="agent-registry-", suffix=".AGENT.md")
        os.close(descriptor)
        return Path(name), True
