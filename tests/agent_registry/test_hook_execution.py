from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from ai_toolkit.agent_registry.errors import PathEscapeError
from ai_toolkit.agent_registry.hook_invocation import HookInvocation
from ai_toolkit.agent_registry.hooks import HookExecutor
from ai_toolkit.agent_registry.models import AuditEvent, HookDefinition


class TestClock:
    def __init__(self) -> None:
        self.current = 10.0

    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)

    def monotonic(self) -> float:
        self.current += 0.25
        return self.current


class TestAudit:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


def _hook(
    directory: Path, *, enabled: bool = True, policy: str = "warn"
) -> HookDefinition:
    return HookDefinition(
        "check",
        "1",
        ("register",),
        enabled,
        ("./run-hook", "--safe"),
        2.0,
        policy,
        True,
        directory,
    )


def _result(
    code: int, output: str = "ok", error: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["./run-hook"], code, output, error)


def test_disabled_hooks_never_invoke_runner_or_audit(tmp_path: Path) -> None:
    calls: list[HookInvocation] = []
    audit = TestAudit()

    def runner(invocation: HookInvocation) -> subprocess.CompletedProcess[str]:
        calls.append(invocation)
        return _result(0)

    result = HookExecutor(runner, TestClock(), audit).execute(
        _hook(tmp_path, enabled=False), "repo", "1"
    )

    assert result.outcome == "disabled"
    assert not calls
    assert not audit.events


def test_executor_uses_shell_free_argv_cwd_and_records_success(tmp_path: Path) -> None:
    calls: list[HookInvocation] = []
    audit = TestAudit()

    def runner(invocation: HookInvocation) -> subprocess.CompletedProcess[str]:
        calls.append(invocation)
        return _result(0, "normal output")

    result = HookExecutor(runner, TestClock(), audit).execute(
        _hook(tmp_path), "repo", "1"
    )

    assert result.outcome == "success"
    assert result.duration == 0.25
    assert calls[0].argv == ("./run-hook", "--safe")
    assert calls[0].shell is False
    assert calls[0].cwd == tmp_path
    assert audit.events[0].operation == "hook:check"
    assert audit.events[0].repository_id == "repo"
    assert audit.events[0].metadata["output"] == "normal output"


@pytest.mark.parametrize(
    ("policy", "blocked"), [("block", True), ("warn", False), ("ignore", False)]
)
def test_executor_applies_nonzero_failure_policy(
    tmp_path: Path, policy: str, blocked: bool
) -> None:
    audit = TestAudit()

    def runner(invocation: HookInvocation) -> subprocess.CompletedProcess[str]:
        return _result(7, "", "failed")

    result = HookExecutor(runner, TestClock(), audit).execute(
        _hook(tmp_path, policy=policy), "repo", "1"
    )

    assert result.outcome == "failed"
    assert result.returncode == 7
    assert result.blocked is blocked
    assert audit.events[0].outcome == "failed"


def test_executor_classifies_timeout_and_sanitizes_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOOK_SECRET", "never-persist")
    audit = TestAudit()

    def runner(invocation: HookInvocation) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            "./run-hook",
            invocation.timeout,
            output="TOKEN=never-persist",
            stderr="password=never-persist",
        )

    result = HookExecutor(runner, TestClock(), audit).execute(
        _hook(tmp_path, policy="block"), "repo", "1"
    )

    assert result.outcome == "timeout"
    assert result.blocked
    assert "never-persist" not in result.stdout
    assert "never-persist" not in result.stderr
    assert "never-persist" not in str(audit.events[0].to_json())


def test_executor_rejects_path_escape_even_for_direct_hook_definition(
    tmp_path: Path,
) -> None:
    hook = HookDefinition(
        "check",
        "1",
        ("register",),
        True,
        ("../outside",),
        2.0,
        "block",
        False,
        tmp_path,
    )

    with pytest.raises(PathEscapeError):
        HookExecutor(clock=TestClock()).execute(hook)
