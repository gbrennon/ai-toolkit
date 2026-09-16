import pytest

from ai_toolkit.install_hooks.installers.native_enforcement_installer import (
    NativeEnforcementInstaller,
)

pytestmark = pytest.mark.unit


class TestNativeEnforcementInstaller:
    def test_create_returns_instance(self):
        installer = NativeEnforcementInstaller.create("opencode")

        assert isinstance(installer, NativeEnforcementInstaller)

    def test_install_reports_native_enforcement(self, capsys):
        installer = NativeEnforcementInstaller.create("cline")

        installed = installer.install()

        assert installed is True
        out = capsys.readouterr().out
        assert "cline" in out
        assert "native AGENTS.md enforcement" in out
