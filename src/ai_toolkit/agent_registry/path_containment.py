from dataclasses import dataclass
from pathlib import Path

from .errors import PathEscapeError


@dataclass(frozen=True, slots=True)
class PathContainment:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.expanduser().resolve())

    def resolve(self, reference: Path | str) -> Path:
        reference_path = Path(reference)
        if reference_path.is_absolute() or ".." in reference_path.parts:
            raise PathEscapeError(self._message(reference_path))
        candidate = (self.root / reference_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise PathEscapeError(self._message(reference_path))
        return candidate

    def _message(self, reference: Path) -> str:
        return f"path {reference!s} escapes registry root {self.root!s}"
