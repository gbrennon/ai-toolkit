import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path

from .atomic_writer import AtomicWriter
from .errors import MalformedDocumentError

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]


def as_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [as_json_value(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: as_json_value(item) for key, item in value.items()}
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class JsonDocumentStore:
    _writer: AtomicWriter = field(default_factory=AtomicWriter)

    def read(self, path: Path) -> JsonValue:
        try:
            return as_json_value(json.loads(path.read_text(encoding="utf-8")))
        except (JSONDecodeError, UnicodeDecodeError, TypeError) as error:
            raise MalformedDocumentError(f"malformed JSON document {path!s}: {error}") from error

    def write(self, path: Path, document: JsonValue) -> None:
        encoded = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
        self._writer.write_text(path, f"{encoded}\n")
