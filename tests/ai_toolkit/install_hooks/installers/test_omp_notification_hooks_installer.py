from pathlib import Path

import pytest

from ai_toolkit.install_hooks.installers.omp_notification_hooks_installer import (
    OMP_NOTIFICATION_HOOK_PATH,
    OmpNotificationHooksInstaller,
)

pytestmark = pytest.mark.integration


class TestOmpNotificationHooksInstaller:
    def test_create_targets_default_hook_path(self) -> None:
        installer = OmpNotificationHooksInstaller.create()

        assert installer.hook_path == OMP_NOTIFICATION_HOOK_PATH

    def test_install_writes_notification_hook(self, tmp_path: Path) -> None:
        target = tmp_path / "hooks" / "post" / "notify.ts"

        installed = OmpNotificationHooksInstaller.create(target).install()

        assert installed is True
        content = target.read_text(encoding="utf-8")
        assert 'pi.on("turn_end"' in content
        assert "process.env.TMUX" in content
        assert "#{session_name}" in content
        assert "display-message" in content
        assert "notify-send" in content

    def test_install_is_deterministic(self, tmp_path: Path) -> None:
        target = tmp_path / "notify.ts"
        installer = OmpNotificationHooksInstaller.create(target)

        installer.install()
        first_content = target.read_text(encoding="utf-8")
        installer.install()
        second_content = target.read_text(encoding="utf-8")

        assert first_content == second_content

    def test_install_returns_false_when_write_fails(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        blocking_file = tmp_path / "blocker"
        blocking_file.write_text("not a directory", encoding="utf-8")
        target = blocking_file / "notify.ts"

        installed = OmpNotificationHooksInstaller.create(target).install()

        assert installed is False
        assert "OMP notification hook failed" in capsys.readouterr().err
