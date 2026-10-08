from .registry_error import RegistryError


class InvalidOperationError(RegistryError):
    """Raised when a registry operation cannot proceed safely."""
