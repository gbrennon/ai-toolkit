from collections.abc import Mapping
import os
import re
from typing import TypeAlias, cast

JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)

_SENSITIVE_KEY = re.compile(
    r"(?:secret|token|password|passwd|api[-_]?key|authorization|credential|cookie|private[-_]?key|environment|env)",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(?:secret|token|password|passwd|api[-_]?key|authorization|credential)\s*[=:]\s*[^\s,;]+"
)
_BEARER = re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
_TOKEN_PREFIX = re.compile(
    r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+|xox[baprs]-[A-Za-z0-9-]+)\b"
)
_MAX_TEXT = 16_384


def sanitize_metadata(value: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Return metadata with sensitive keys, values, and environment text removed."""
    return {
        key: _sanitize_value(key, item)
        for key, item in value.items()
        if isinstance(key, str) and not _SENSITIVE_KEY.search(key)
    }


def sanitize_text(value: str, *, limit: int = _MAX_TEXT) -> str:
    """Redact common secret forms and inherited environment values from text."""
    result = _SECRET_ASSIGNMENT.sub(
        lambda match: match.group(0).split("=", 1)[0].split(":", 1)[0] + "=<redacted>",
        value,
    )
    result = _BEARER.sub("<redacted-credential>", result)
    result = _TOKEN_PREFIX.sub("<redacted-token>", result)
    for environment_value in _environment_values():
        result = result.replace(environment_value, "<redacted-environment>")
    return result[:limit]


def _sanitize_value(key: str, value: JsonValue) -> JsonValue:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, Mapping):
        return sanitize_metadata(cast(Mapping[str, JsonValue], value))
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    return value


def _environment_values() -> tuple[str, ...]:
    return tuple(
        sorted(
            (item for item in os.environ.values() if len(item) >= 4),
            key=len,
            reverse=True,
        )
    )
