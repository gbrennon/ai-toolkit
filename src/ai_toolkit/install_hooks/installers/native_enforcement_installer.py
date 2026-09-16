from typing import Self


class NativeEnforcementInstaller:
    """Report native AGENTS.md enforcement for agents without pi-hooks."""

    def __init__(self, agent: str) -> None:
        self._agent = agent

    @classmethod
    def create(cls, agent: str) -> Self:
        """Return an installer for a native-enforcement agent."""
        return cls(agent)

    def install(self) -> bool:
        print(
            f"  {self._agent}: hooks via native AGENTS.md enforcement "
            f"(no pi-hooks needed)"
        )
        return True
