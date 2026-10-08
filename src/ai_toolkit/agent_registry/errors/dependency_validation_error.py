from .schema_validation_error import SchemaValidationError


class DependencyValidationError(SchemaValidationError):
    """Raised when a skill or hook dependency cannot be validated."""
