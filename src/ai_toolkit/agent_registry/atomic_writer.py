import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .errors import AtomicWriteError


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


def _write_atomic(path: Path, payload: bytes) -> None:
    _prepare_parent(path)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@dataclass(frozen=True, slots=True)
class AtomicWriter:
    def write_bytes(self, path: Path, value: bytes) -> None:
        try:
            _write_atomic(path, value)
        except Exception as error:
            raise AtomicWriteError(f"atomic write failed for {path!s}: {error}") from error

    def write_text(self, path: Path, value: str) -> None:
        self.write_bytes(path, value.encode("utf-8"))
