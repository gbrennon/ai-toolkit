from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from ai_toolkit.agent_notify.command_runner import _CommandRunner
from ai_toolkit.agent_notify.notification import Notification
from ai_toolkit.agent_notify.tmux_identity import TmuxIdentity


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
    try:
        result = _run_tmux_command(cwd, active_environment, run)
    except OSError:
        return _none_identity()
    if result.returncode != 0:
        return _none_identity()
    return _identity_from_tmux_output(result.stdout)


def format_notification_body(notification: Notification) -> str:
    """Format notification details into a readable multiline desktop body."""
    return "\n".join(
        (
            f"window={notification.identity.window_index}:"
            f"{notification.identity.window_name}",
            f"session={notification.identity.session_name}",
            f"cwd={notification.cwd}",
            f"message={notification.message}",
        )
    )


def format_notification_title(notification: Notification) -> str:
    """Format the concise notification header from the agent and event."""
    return f"{notification.agent} {notification.event}"


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
            format_notification_title(notification),
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
    return 0 if send_notification(notification) else 1


if __name__ == "__main__":
    raise SystemExit(main())
