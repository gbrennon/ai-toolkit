from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class HookInvocation:
    """Describe one shell-free hook subprocess invocation."""

    argv: Sequence[str]
    cwd: Path
    timeout: float
    shell: bool = False
    capture_output: bool = True
    text: bool = True
    check: bool = False
