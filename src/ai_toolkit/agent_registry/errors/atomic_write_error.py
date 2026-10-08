from .registry_error import RegistryError


class AtomicWriteError(RegistryError):
    """Raised when an atomic registry write cannot complete."""
