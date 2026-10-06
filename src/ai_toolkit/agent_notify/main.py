from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class _CommandRunner(Protocol):
    def __call__(
        self,
        args: Sequence[str],
        *,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        capture_output: bool = False,
        text: bool | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True)
class TmuxIdentity:
    """Identifies the tmux window that owns an agent process."""

    session_name: str
    window_index: str
    window_name: str


@dataclass(frozen=True)
class Notification:
    """Describes one agent lifecycle notification."""

    agent: str
    event: str
    cwd: Path
    identity: TmuxIdentity
    message: str


def _none_identity() -> TmuxIdentity:
    return TmuxIdentity(session_name="none", window_index="none", window_name="none")


def _run_tmux_command(
    cwd: Path,
    environment: Mapping[str, str],
    run: _CommandRunner | None,
) -> subprocess.CompletedProcess[str]:
    active_run = subprocess.run if run is None else run
    return active_run(
        [
            "tmux",
            "display-message",
            "-p",
            "-F",
            "#{session_name}|#{window_index}|#{window_name}",
        ],
        cwd=cwd,
        env=dict(environment),
        capture_output=True,
        text=True,
        check=False,
    )


def _identity_from_tmux_output(output: str) -> TmuxIdentity:
    fields = output.strip().split("|", maxsplit=2)
    if len(fields) != 3:
        return _none_identity()
    session_name, window_index, window_name = fields
    if not session_name or not window_index or not window_name:
        return _none_identity()
    return TmuxIdentity(
        session_name=session_name,
        window_index=window_index,
        window_name=window_name,
    )


def notification_from_tmux(
    *,
    cwd: Path,
    environment: Mapping[str, str] | None = None,
    run: _CommandRunner | None = None,
) -> TmuxIdentity:
    """Read the current tmux session and window identity, or return fallbacks."""
    active_environment = os.environ if environment is None else environment
    if "TMUX" not in active_environment:
        return _none_identity()
    result = _run_tmux_command(cwd, active_environment, run)
    if result.returncode != 0:
        return _none_identity()
    return _identity_from_tmux_output(result.stdout)


def format_notification_body(notification: Notification) -> str:
    """Format notification fields into a stable, searchable desktop message."""
    return (
        f"agent={notification.agent} event={notification.event} "
        f"session={notification.identity.session_name} "
        f"window_index={notification.identity.window_index} "
        f"window_name={notification.identity.window_name} "
        f"cwd={notification.cwd} message={notification.message}"
    )


def send_notification(
    notification: Notification,
    *,
    run: _CommandRunner | None = None,
    find_command: Callable[[str], str | None] = shutil.which,
) -> bool:
    """Send a desktop notification and report whether delivery was attempted successfully."""
    if find_command("notify-send") is None:
        return False
    active_run = subprocess.run if run is None else run
    result = active_run(
        [
            "notify-send",
            f"{notification.agent} {notification.event}",
            format_notification_body(notification),
        ],
        check=False,
    )
    return result.returncode == 0


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send an agent lifecycle notification")
    parser.add_argument("agent")
    parser.add_argument("event", choices=("question", "complete", "error"))
    parser.add_argument("--message", default="")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Send one best-effort notification for an agent lifecycle event."""
    arguments = _arguments(argv)
    notification = Notification(
        agent=arguments.agent,
        event=arguments.event,
        cwd=arguments.cwd,
        identity=notification_from_tmux(cwd=arguments.cwd),
        message=arguments.message,
    )
    send_notification(notification)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
