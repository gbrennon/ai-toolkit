from .registry_error import RegistryError


class MalformedDocumentError(RegistryError):
    """Raised when a registry document is not valid JSON content."""
