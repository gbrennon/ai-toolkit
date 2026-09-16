from pathlib import Path

import pytest

from ai_toolkit.install_hooks.installers.cline_hooks_installer import (
    CLINE_HOOK_PATH,
    ClineHooksInstaller,
)

pytestmark = pytest.mark.integration


class TestClineHooksInstaller:
    def test_create_targets_default_plugin_path(self) -> None:
        installer = ClineHooksInstaller.create()

        assert installer.plugin_path == CLINE_HOOK_PATH

    def test_install_writes_quality_plugin(self, tmp_path: Path) -> None:
        target = tmp_path / "plugins" / "quality.ts"

        installed = ClineHooksInstaller.create(target).install()

        assert installed is True
        content = target.read_text(encoding="utf-8")
        assert "afterTool" in content
        assert '"check-code-quality"' in content
        assert '"py"' in content
        assert '"md"' not in content
