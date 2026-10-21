from dataclasses import dataclass
from pathlib import Path

from .instruction_source_kind import InstructionSourceKind


@dataclass(frozen=True, slots=True)
class InstructionSource:
    """Describe a candidate instruction file without loading its content."""

    kind: InstructionSourceKind
    path: Path
    exists: bool

    def __post_init__(self) -> None:
        resolved = self.path.expanduser().resolve()
        if not self.path.is_absolute() or self.path != resolved:
            raise ValueError("instruction source path must be absolute and resolved")
