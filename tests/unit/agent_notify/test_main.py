from collections.abc import Sequence
from pathlib import Path

import subprocess

from ai_toolkit.agent_notify.main import (
    Notification,
    TmuxIdentity,
    format_notification_body,
    notification_from_tmux,
    send_notification,
)


def test_notification_body_contains_agent_event_and_tmux_window_identity() -> None:
    notification = Notification(
        agent="omp",
        event="question",
        cwd=Path("/repo"),
        identity=TmuxIdentity(
            session_name="ai-toolkit",
            window_index="2",
            window_name="ws-feat-autonomous-agent-notifications",
        ),
        message="Scope is ambiguous",
    )

    body = format_notification_body(notification)

    assert body == (
        "agent=omp event=question session=ai-toolkit window_index=2 "
        "window_name=ws-feat-autonomous-agent-notifications cwd=/repo "
        "message=Scope is ambiguous"
    )


def test_notification_from_tmux_reads_session_window_index_and_name() -> None:
    completed = subprocess.CompletedProcess(
        args=["tmux"],
        returncode=0,
        stdout="ai-toolkit|2|ws-feat-autonomous-agent-notifications\n",
    )
    calls: list[tuple[Sequence[str], dict[str, object]]] = []

    def fake_run(
        args: Sequence[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return completed

    identity = notification_from_tmux(
        cwd=Path("/repo"),
        environment={"TMUX": "/tmp/tmux"},
        run=fake_run,
    )

    assert calls == [
        (
            [
                "tmux",
                "display-message",
                "-p",
                "-F",
                "#{session_name}|#{window_index}|#{window_name}",
            ],
            {
                "cwd": Path("/repo"),
                "env": {"TMUX": "/tmp/tmux"},
                "capture_output": True,
                "text": True,
                "check": False,
            },
        )
    ]
    assert identity == TmuxIdentity(
        session_name="ai-toolkit",
        window_index="2",
        window_name="ws-feat-autonomous-agent-notifications",
    )


def test_notification_from_tmux_uses_none_identity_outside_tmux() -> None:
    identity = notification_from_tmux(
        cwd=Path("/repo"),
        environment={},
    )

    assert identity == TmuxIdentity(
        session_name="none",
        window_index="none",
        window_name="none",
    )


def test_send_notification_delivers_formatted_body() -> None:
    notification = Notification(
        agent="pi",
        event="complete",
        cwd=Path("/repo"),
        identity=TmuxIdentity("session", "2", "ws-feat"),
        message="task complete",
    )
    calls: list[tuple[Sequence[str], dict[str, object]]] = []

    def fake_run(
        args: Sequence[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0)

    delivered = send_notification(
        notification,
        run=fake_run,
        find_command=lambda _: "/usr/bin/notify-send",
    )

    assert delivered is True
    assert calls == [
        (
            [
                "notify-send",
                "pi complete",
                (
                    "agent=pi event=complete session=session window_index=2 "
                    "window_name=ws-feat cwd=/repo message=task complete"
                ),
            ],
            {"check": False},
        )
    ]


def test_send_notification_reports_missing_delivery_command() -> None:
    notification = Notification(
        agent="omp",
        event="error",
        cwd=Path("/repo"),
        identity=TmuxIdentity("none", "none", "none"),
        message="task failed",
    )

    delivered = send_notification(
        notification,
        find_command=lambda _: None,
    )

    assert delivered is False
