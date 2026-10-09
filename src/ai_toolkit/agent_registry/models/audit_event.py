from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import re
from types import MappingProxyType
from typing import cast

from ..audit_sanitizer import sanitize_metadata
from ._json import JsonValue, utc_z

_FIELDS = frozenset(
    {
        "timestamp",
        "operation",
        "repositoryId",
        "configurationVersion",
        "outcome",
        "duration",
        "metadata",
    }
)
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable, validated record of one registry or hook operation."""

    timestamp: datetime
    operation: str
    repository_id: str
    configuration_version: str
    outcome: str
    duration: float
    metadata: Mapping[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", _timestamp(self.timestamp))
        _validate_text(
            self.operation, self.repository_id, self.configuration_version, self.outcome
        )
        object.__setattr__(self, "duration", _validated_duration(self.duration))
        if not isinstance(self.metadata, Mapping):
            raise ValueError("audit metadata must be an object")
        object.__setattr__(
            self, "metadata", _freeze_mapping(sanitize_metadata(self.metadata))
        )

    def to_json(self) -> dict[str, JsonValue]:
        """Return the strict, sanitized NDJSON representation."""
        return {
            "timestamp": utc_z(self.timestamp),
            "operation": self.operation,
            "repositoryId": self.repository_id,
            "configurationVersion": self.configuration_version,
            "outcome": self.outcome,
            "duration": self.duration,
            "metadata": _thaw(self.metadata),
        }

    @classmethod
    def from_json(cls, value: object) -> "AuditEvent":
        """Parse and strictly validate one external audit record."""
        mapping = _strict_mapping(value)
        parsed_timestamp = _parse_timestamp(mapping["timestamp"])
        metadata = mapping["metadata"]
        if not isinstance(metadata, Mapping):
            raise ValueError("audit metadata must be an object")
        return cls(
            parsed_timestamp,
            cast(str, mapping["operation"]),
            cast(str, mapping["repositoryId"]),
            cast(str, mapping["configurationVersion"]),
            cast(str, mapping["outcome"]),
            _validated_duration(mapping["duration"]),
            cast(Mapping[str, JsonValue], metadata),
        )


def _timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("audit timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _validate_text(*values: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("audit text fields must be nonempty strings")


def _validated_duration(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("audit duration must be a finite nonnegative number")
    return float(value)


def _strict_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("audit event must be an object")
    unknown = set(value) - _FIELDS
    missing = _FIELDS - set(value)
    if unknown:
        raise ValueError(f"audit event contains unknown field: {sorted(unknown)[0]}")
    if missing:
        raise ValueError(f"audit event is missing field: {sorted(missing)[0]}")
    return cast(Mapping[str, object], value)


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or _TIMESTAMP.fullmatch(value) is None:
        raise ValueError("audit timestamp must use UTC Z format")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("audit timestamp is invalid") from error


def _freeze_mapping(value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    frozen: dict[str, JsonValue] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError("audit metadata keys must be strings")
        frozen[key] = _freeze_value(item)
    return cast(Mapping[str, JsonValue], MappingProxyType(frozen))


def _freeze_value(value: object) -> JsonValue:
    if isinstance(value, Mapping):
        return cast(JsonValue, _freeze_mapping(cast(Mapping[str, JsonValue], value)))
    if isinstance(value, list):
        return [_freeze_value(item) for item in value]
    return _freeze_scalar(value)


def _freeze_scalar(value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return cast(JsonValue, value)
    raise ValueError("audit metadata must contain JSON values")


def _thaw(value: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    return {key: _thaw_value(item) for key, item in value.items()}


def _thaw_value(value: JsonValue) -> JsonValue:
    if isinstance(value, Mapping):
        return _thaw(cast(Mapping[str, JsonValue], value))
    if isinstance(value, list):
        return [_thaw_value(item) for item in value]
    return value
