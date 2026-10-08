from .registry_error import RegistryError


class SchemaValidationError(RegistryError):
    """Raised when strict registry or dependency schema validation fails."""
