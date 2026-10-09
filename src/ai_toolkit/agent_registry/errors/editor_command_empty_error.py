from .registry_error import RegistryError


class EditorCommandEmptyError(RegistryError):
    """Raised when the selected editor command parses to no arguments."""
