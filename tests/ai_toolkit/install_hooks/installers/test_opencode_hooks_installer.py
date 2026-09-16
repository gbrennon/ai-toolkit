from pathlib import Path

import pytest

from ai_toolkit.install_hooks.installers.opencode_hooks_installer import (
    OPENCODE_HOOK_PATH,
    OpenCodeHooksInstaller,
)

pytestmark = pytest.mark.integration


class TestOpenCodeHooksInstaller:
    def test_create_targets_default_plugin_path(self) -> None:
        installer = OpenCodeHooksInstaller.create()

        assert installer.plugin_path == OPENCODE_HOOK_PATH

    def test_install_writes_quality_plugin(self, tmp_path: Path) -> None:
        target = tmp_path / "plugins" / "quality.ts"

        installed = OpenCodeHooksInstaller.create(target).install()

        assert installed is True
        content = target.read_text(encoding="utf-8")
        assert '"tool.execute.after"' in content
        assert '"check-code-quality"' in content
        assert '"py"' in content
        assert '"md"' not in content
