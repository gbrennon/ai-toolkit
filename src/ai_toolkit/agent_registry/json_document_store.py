import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from .atomic_writer import AtomicWriter
from .errors import MalformedDocumentError


@dataclass(frozen=True, slots=True)
class JsonDocumentStore:
    _writer: AtomicWriter = field(default_factory=AtomicWriter)

    def read(self, path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (JSONDecodeError, UnicodeDecodeError) as error:
            raise MalformedDocumentError(f"malformed JSON document {path!s}: {error}") from error

    def write(self, path: Path, document: Any) -> None:
        encoded = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True)
        self._writer.write_text(path, f"{encoded}\n")
