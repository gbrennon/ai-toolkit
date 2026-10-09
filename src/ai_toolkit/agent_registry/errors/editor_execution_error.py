from .registry_error import RegistryError


class EditorExecutionError(RegistryError):
    """Raised when the selected editor exits unsuccessfully."""
