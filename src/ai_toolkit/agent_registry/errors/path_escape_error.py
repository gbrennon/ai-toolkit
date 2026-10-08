from .registry_error import RegistryError


class PathEscapeError(RegistryError):
    """Raised when a registry path would escape its allowed root."""
