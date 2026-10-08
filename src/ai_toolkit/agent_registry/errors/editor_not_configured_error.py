from .registry_error import RegistryError


class EditorNotConfiguredError(RegistryError):
    """Raised when neither VISUAL nor EDITOR is configured."""
