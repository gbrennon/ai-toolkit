from datetime import datetime, timezone
import math
from pathlib import Path
import subprocess
import time

from .audit_sanitizer import sanitize_text
from .audit_sink import AuditSink
from .errors import PathEscapeError, SchemaValidationError
from .hook_clock import HookClock
from .hook_invocation import HookInvocation
from .hook_runner import HookRunner
from .models import AuditEvent, HookDefinition, HookExecutionResult
from .path_containment import PathContainment


class HookExecutor:
    """Execute validated global hooks with safe subprocess and audit seams."""

    def __init__(
        self,
        runner: HookRunner | None = None,
        clock: HookClock | None = None,
        audit: AuditSink | None = None,
    ) -> None:
        self._runner = _run_subprocess if runner is None else runner
        self._clock = clock
        self._audit = audit

    def execute(
        self,
        hook: HookDefinition,
        repository_id: str = "unknown",
        configuration_version: str = "unknown",
    ) -> HookExecutionResult:
        """Execute one enabled hook and apply its declared failure policy."""
        _validate_hook(hook)
        if not hook.enabled:
            return HookExecutionResult(hook.id, "disabled", None, False, 0.0, "", "")
        started = self._monotonic()
        outcome, returncode, stdout, stderr = self._invoke(hook)
        duration = max(0.0, self._monotonic() - started)
        blocked = outcome != "success" and hook.failure_policy == "block"
        result = HookExecutionResult(
            hook.id, outcome, returncode, blocked, duration, stdout, stderr
        )
        self._record(hook, result, repository_id, configuration_version)
        return result

    def _invoke(self, hook: HookDefinition) -> tuple[str, int | None, str, str]:
        try:
            completed = self._runner(
                HookInvocation(hook.argv, hook.directory, hook.timeout)
            )
        except subprocess.TimeoutExpired as error:
            return "timeout", None, _text(error.stdout), _text(error.stderr)
        except OSError as error:
            return "failed", None, "", sanitize_text(str(error))
        stdout = sanitize_text(_text(completed.stdout))
        stderr = sanitize_text(_text(completed.stderr))
        outcome = "success" if completed.returncode == 0 else "failed"
        return outcome, completed.returncode, stdout, stderr

    def _record(
        self,
        hook: HookDefinition,
        result: HookExecutionResult,
        repository_id: str,
        configuration_version: str,
    ) -> None:
        if not hook.audit or self._audit is None:
            return
        self._audit.record(
            AuditEvent(
                self._now(),
                f"hook:{hook.id}",
                repository_id,
                configuration_version,
                result.outcome,
                result.duration,
                {
                    "hookId": hook.id,
                    "failurePolicy": hook.failure_policy,
                    "blocked": result.blocked,
                    "returncode": result.returncode,
                    "output": result.stdout,
                    "error": result.stderr,
                },
            )
        )

    def _now(self) -> datetime:
        return datetime.now(timezone.utc) if self._clock is None else self._clock.now()

    def _monotonic(self) -> float:
        return time.monotonic() if self._clock is None else self._clock.monotonic()


def _run_subprocess(invocation: HookInvocation) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(invocation.argv),
        cwd=invocation.cwd,
        timeout=invocation.timeout,
        shell=invocation.shell,
        capture_output=invocation.capture_output,
        text=invocation.text,
        check=invocation.check,
    )


def _validate_hook(hook: HookDefinition) -> None:
    _validate_identity(hook)
    _validate_argv(hook)
    _validate_timeout(hook.timeout)
    if hook.failure_policy not in {"block", "warn", "ignore"}:
        raise SchemaValidationError(
            "hook failure policy must be block, warn, or ignore"
        )


def _validate_identity(hook: HookDefinition) -> None:
    if not hook.id.strip() or not hook.version.strip():
        raise SchemaValidationError("hook identity must be nonempty")


def _validate_argv(hook: HookDefinition) -> None:
    if not hook.argv:
        raise SchemaValidationError("hook argv must be a nonempty sequence of strings")
    containment = PathContainment(hook.directory.expanduser().resolve())
    for component in hook.argv:
        _validate_component(component, containment)


def _validate_component(component: str, containment: PathContainment) -> None:
    if not isinstance(component, str) or not component:
        raise SchemaValidationError("hook argv must contain nonempty strings")
    candidate = Path(component)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise PathEscapeError(
            f"hook executable path escapes hook directory: {component}"
        )
    containment.resolve(candidate)


def _validate_timeout(timeout: float) -> None:
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise SchemaValidationError("hook timeout must be a positive finite number")


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return sanitize_text(value.decode("utf-8", errors="replace"))
    return sanitize_text(value)
