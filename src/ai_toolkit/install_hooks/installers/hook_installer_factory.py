from collections.abc import Callable, Sequence

from ai_toolkit.install_hooks.installers.hook_installer import HookInstaller
from ai_toolkit.install_hooks.installers.cline_hooks_installer import (
    ClineHooksInstaller,
)
from ai_toolkit.install_hooks.installers.omp_hooks_installer import OmpHooksInstaller
from ai_toolkit.install_hooks.installers.opencode_hooks_installer import (
    OpenCodeHooksInstaller,
)
from ai_toolkit.install_hooks.installers.pi_hooks_installer import PiHooksInstaller
from ai_toolkit.install_hooks.installers.omp_notification_hooks_installer import (
    OmpNotificationHooksInstaller,
)


class HookInstallerFactory:
    """Resolve an agent selector to the ordered hook installers to run."""

    @classmethod
    def create(cls, agent: str) -> Sequence[HookInstaller]:
        builders = cls._builders_for(agent)
        return [build() for build in builders]

    @classmethod
    def _builders_for(cls, agent: str) -> Sequence[Callable[[], HookInstaller]]:
        return cls._selectors().get(agent, [])

    @classmethod
    def _selectors(cls) -> dict[str, Sequence[Callable[[], HookInstaller]]]:
        return {
            "all": [
                PiHooksInstaller.create,
                OmpHooksInstaller.create,
                OpenCodeHooksInstaller.create,
                ClineHooksInstaller.create,
                OmpNotificationHooksInstaller.create,
            ],
            "pi": [PiHooksInstaller.create],
            "omp": [OmpHooksInstaller.create, OmpNotificationHooksInstaller.create],
            "opencode": [OpenCodeHooksInstaller.create],
            "cline": [ClineHooksInstaller.create],
        }
