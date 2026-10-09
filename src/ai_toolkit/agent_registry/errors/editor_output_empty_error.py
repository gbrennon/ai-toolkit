from .registry_error import RegistryError


class EditorOutputEmptyError(RegistryError):
    """Raised when an editor exits successfully without AGENT.md content."""
