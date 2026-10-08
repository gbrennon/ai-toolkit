from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class GitInvocation:
    """Describe one shell-free Git subprocess invocation."""

    args: Sequence[str]
    cwd: Path
    check: bool = False
    capture_output: bool = True
    text: bool = True
    shell: bool = False
