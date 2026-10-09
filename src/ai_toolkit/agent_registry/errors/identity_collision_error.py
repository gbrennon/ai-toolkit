from .registry_error import RegistryError


class IdentityCollisionError(RegistryError):
    """Report a duplicate normalized remote, path, or repository ID."""

    def __init__(self, identity: str, reason: str) -> None:
        self.identity = identity
        self.reason = reason
        super().__init__(f"identity collision for {identity!r}: {reason}")
