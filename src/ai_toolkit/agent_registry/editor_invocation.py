from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EditorInvocation:
    """Describe one shell-free editor subprocess invocation."""

    argv: Sequence[str]
    path: Path
    environment: Mapping[str, str]
    shell: bool = False
    capture_output: bool = True
    text: bool = True
    check: bool = False
