from pathlib import Path

import pytest

from ai_toolkit.install_hooks.installers.omp_hooks_installer import (
    OMP_HOOK_PATH,
    OmpHooksInstaller,
)

pytestmark = pytest.mark.integration


class TestOmpHooksInstaller:
    def test_create_targets_default_hook_path(self) -> None:
        installer = OmpHooksInstaller.create()

        assert installer.hook_path == OMP_HOOK_PATH

    def test_install_writes_native_omp_hook(self, tmp_path: Path) -> None:
        target = tmp_path / "hooks" / "post" / "quality.ts"

        installed = OmpHooksInstaller.create(target).install()

        assert installed is True
        content = target.read_text(encoding="utf-8")
        assert 'pi.on("tool_result"' in content
        assert '"check-code-quality"' in content
        assert '"py"' in content
        assert '"md"' not in content

    def test_install_is_deterministic(self, tmp_path: Path) -> None:
        target = tmp_path / "quality.ts"
        installer = OmpHooksInstaller.create(target)

        installer.install()
        first_content = target.read_text(encoding="utf-8")
        installer.install()
        second_content = target.read_text(encoding="utf-8")

        assert first_content == second_content
