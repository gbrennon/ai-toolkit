import json
import os
import subprocess
from pathlib import Path

import pytest

from ai_toolkit.install_hooks.installers.pi_hooks_installer import (
    CODE_EXTENSIONS,
    HOOK_MATCHER,
    HOOK_PACKAGE,
    NOTIFICATION_CMD,
    PiHooksInstaller,
    install_hooks,
)

pytestmark = pytest.mark.integration


def _expected_tool_conditions() -> set[str]:
    return {
        f"{tool}(*.{ext})"
        for tool in ("Write", "Edit")
        for ext in CODE_EXTENSIONS
    }


class TestPiHooksInstaller:
    def test_install_hooks_copies_hook_from_package_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        assert install_hooks() is True

        installed_hook = tmp_path / ".hooks" / "pr_opened_hook.py"
        assert installed_hook.is_file()
        assert "class PROpenedHook" in installed_hook.read_text(encoding="utf-8")

    def test_install_writes_hook_and_package_to_new_file(self, tmp_path):
        target = tmp_path / "settings.json"

        installed = PiHooksInstaller.create(target).install()

        assert installed is True
        data = json.loads(target.read_text(encoding="utf-8"))
        groups = data["hooks"]["PostToolUse"]
        assert len(groups) == 1
        assert groups[0]["matcher"] == HOOK_MATCHER
        hooks = groups[0]["hooks"]
        conditions = {hook["if"] for hook in hooks}
        assert conditions == _expected_tool_conditions()
        assert all(
            hook["type"] == "command"
            and hook["command"] == "check-modified-code-quality"
            for hook in hooks
        )
        assert HOOK_PACKAGE in data["packages"]

    def test_install_writes_stop_notification_hook(self, tmp_path):
        target = tmp_path / "settings.json"

        PiHooksInstaller.create(target).install()

        data = json.loads(target.read_text(encoding="utf-8"))
        groups = data["hooks"]["Stop"]
        assert len(groups) == 1
        assert "matcher" not in groups[0]
        hooks = groups[0]["hooks"]
        assert len(hooks) == 1
        assert hooks[0]["type"] == "command"
        assert hooks[0]["command"] == NOTIFICATION_CMD
        assert "client_session" in hooks[0]["command"]
        assert "window_active" in hooks[0]["command"]

    def test_stop_notification_command_has_valid_shell_syntax(self) -> None:
        result = subprocess.run(
            ["sh", "-n"],
            input=NOTIFICATION_CMD,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr

    def test_install_merges_without_clobbering_existing(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

        installed = PiHooksInstaller.create(target).install()

        assert installed is True
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["theme"] == "dark"
        assert HOOK_PACKAGE in data["packages"]

    def test_install_does_not_duplicate_package(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text(
            json.dumps({"packages": [HOOK_PACKAGE]}), encoding="utf-8"
        )

        PiHooksInstaller.create(target).install()

        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["packages"].count(HOOK_PACKAGE) == 1

    def test_install_replaces_existing_hook_config(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text(
            json.dumps({"hooks": {"PostToolUse": [{}]}}), encoding="utf-8"
        )

        PiHooksInstaller.create(target).install()

        data = json.loads(target.read_text(encoding="utf-8"))
        assert len(data["hooks"]["PostToolUse"]) == 1
        assert data["hooks"]["PostToolUse"][0]["matcher"] == HOOK_MATCHER

    def test_install_returns_false_when_write_fails(self, tmp_path, capsys):
        target = tmp_path / "settings.json"
        target.mkdir()

        installed = PiHooksInstaller.create(target).install()

        assert installed is False
        assert "Pi hook failed" in capsys.readouterr().err

    def test_install_is_deterministic(self, tmp_path):
        target1 = tmp_path / "settings1.json"
        target2 = tmp_path / "settings2.json"

        PiHooksInstaller.create(target1).install()
        PiHooksInstaller.create(target2).install()

        data1 = json.loads(target1.read_text(encoding="utf-8"))
        data2 = json.loads(target2.read_text(encoding="utf-8"))

        assert (
            json.dumps(data1, sort_keys=True)
            == json.dumps(data2, sort_keys=True)
        ), "Multiple runs should produce identical settings"


def run_notification_command(
    tmp_path: Path,
    tmux_output: str,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    tmux = bin_dir / "tmux"
    tmux.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$TMUX_OUTPUT\"\n",
        encoding="utf-8",
    )
    tmux.chmod(0o755)
    notify_send = bin_dir / "notify-send"
    notify_send.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$NOTIFY_LOG\"\n",
        encoding="utf-8",
    )
    notify_send.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "TMUX": "tmux-socket",
        "TMUX_OUTPUT": tmux_output,
        "NOTIFY_LOG": str(tmp_path / "notify.log"),
    }
    return subprocess.run(
        ["sh", "-c", NOTIFICATION_CMD],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def test_notification_command_includes_tmux_session_name() -> None:
    assert "#{session_name}|#{client_session}|#{window_active}" in NOTIFICATION_CMD


def test_notification_command_includes_session_name_in_message(
    tmp_path: Path,
) -> None:
    result = run_notification_command(tmp_path, "project|client|0")

    assert result.returncode == 0
    assert (tmp_path / "notify.log").read_text(encoding="utf-8").splitlines() == [
        "pi agent",
        f"pi: attention needed in {tmp_path} (tmux project)",
    ]


def test_notification_command_suppresses_visible_tmux_window(
    tmp_path: Path,
) -> None:
    result = run_notification_command(tmp_path, "project|client|1")

    assert result.returncode == 0
    assert not (tmp_path / "notify.log").exists()
