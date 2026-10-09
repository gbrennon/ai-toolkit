from .registry_error import RegistryError


class RemoteNormalizationError(RegistryError):
    """Report a remote URL that cannot produce a canonical identity."""

    def __init__(self, remote: str, reason: str) -> None:
        self.remote = remote
        self.reason = reason
        super().__init__(f"cannot normalize remote {remote!r}: {reason}")
