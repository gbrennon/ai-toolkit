import pytest

from ai_toolkit.install_hooks.installers.hook_installer_factory import (
    HookInstallerFactory,
)
from ai_toolkit.install_hooks.installers.cline_hooks_installer import ClineHooksInstaller
from ai_toolkit.install_hooks.installers.omp_hooks_installer import OmpHooksInstaller
from ai_toolkit.install_hooks.installers.opencode_hooks_installer import (
    OpenCodeHooksInstaller,
)
from ai_toolkit.install_hooks.installers.pi_hooks_installer import PiHooksInstaller

pytestmark = pytest.mark.unit


class TestHookInstallerFactory:
    def test_pi_selects_pi_installer(self):
        installers = HookInstallerFactory.create("pi")

        assert len(installers) == 1
        assert isinstance(installers[0], PiHooksInstaller)

    def test_opencode_selects_opencode_installer(self):
        installers = HookInstallerFactory.create("opencode")

        assert len(installers) == 1
        assert isinstance(installers[0], OpenCodeHooksInstaller)

    def test_cline_selects_cline_installer(self):
        installers = HookInstallerFactory.create("cline")

        assert len(installers) == 1
        assert isinstance(installers[0], ClineHooksInstaller)

    def test_omp_selects_omp_installer(self):
        installers = HookInstallerFactory.create("omp")

        assert len(installers) == 1
        assert isinstance(installers[0], OmpHooksInstaller)

    def test_all_selects_every_agent_hook_installer(self):
        installers = HookInstallerFactory.create("all")

        assert len(installers) == 4
        assert isinstance(installers[0], PiHooksInstaller)
        assert isinstance(installers[1], OmpHooksInstaller)
        assert isinstance(installers[2], OpenCodeHooksInstaller)
        assert isinstance(installers[3], ClineHooksInstaller)
