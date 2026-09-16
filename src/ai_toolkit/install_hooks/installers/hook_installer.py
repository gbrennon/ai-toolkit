from typing import Protocol


class HookInstaller(Protocol):
    def install(self) -> bool: ...
