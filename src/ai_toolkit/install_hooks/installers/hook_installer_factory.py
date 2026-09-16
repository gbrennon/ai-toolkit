from collections.abc import Sequence

from ai_toolkit.install_hooks.installers.hook_installer import HookInstaller
from ai_toolkit.install_hooks.installers.cline_hooks_installer import (
    ClineHooksInstaller,
)
from ai_toolkit.install_hooks.installers.omp_hooks_installer import OmpHooksInstaller
from ai_toolkit.install_hooks.installers.opencode_hooks_installer import (
    OpenCodeHooksInstaller,
)
from ai_toolkit.install_hooks.installers.pi_hooks_installer import PiHooksInstaller


class HookInstallerFactory:
    """Resolve an agent selector to the ordered hook installers to run."""

    @classmethod
    def create(cls, agent: str) -> Sequence[HookInstaller]:
        if agent == "all":
            return [
                PiHooksInstaller.create(),
                OmpHooksInstaller.create(),
                OpenCodeHooksInstaller.create(),
                ClineHooksInstaller.create(),
            ]
        if agent == "pi":
            return [PiHooksInstaller.create()]
        if agent == "omp":
            return [OmpHooksInstaller.create()]
        if agent == "opencode":
            return [OpenCodeHooksInstaller.create()]
        if agent == "cline":
            return [ClineHooksInstaller.create()]
        return []
