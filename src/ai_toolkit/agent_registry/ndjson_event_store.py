import json
import os
from dataclasses import dataclass
from pathlib import Path

from .errors import MalformedDocumentError
from .json_document_store import JsonValue, as_json_value


def _prepare_parent(path: Path) -> None:
    parent = path.parent
    missing: list[Path] = []
    current = parent
    while not current.exists():
        missing.append(current)
        current = current.parent
    parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        parent.chmod(0o700)
        for directory in missing:
            directory.chmod(0o700)


def _decode_event(path: Path, line_number: int, line: str) -> dict[str, JsonValue]:
    try:
        event = as_json_value(json.loads(line))
        if not isinstance(event, dict):
            raise ValueError("record is not a JSON object")
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise MalformedDocumentError(
            f"malformed NDJSON document {path!s} at line {line_number}: {error}"
        ) from error
    return event


@dataclass(frozen=True, slots=True)
class NdjsonEventStore:
    def append(self, path: Path, event: dict[str, JsonValue]) -> None:
        _prepare_parent(path)
        with path.open("a", encoding="utf-8") as handle:
            if os.name != "nt":
                path.chmod(0o600)
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

    def read(self, path: Path) -> list[dict[str, JsonValue]]:
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as error:
            raise MalformedDocumentError(
                f"malformed NDJSON document {path!s} at line 1: {error}"
            ) from error
        return [
            _decode_event(path, line_number, line)
            for line_number, line in enumerate(lines, start=1)
        ]
