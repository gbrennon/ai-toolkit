from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol


class _CommandRunner(Protocol):
    """Describe the subprocess runner required by notification adapters."""

    def __call__(
        self,
        args: Sequence[str],
        *,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        capture_output: bool = False,
        text: bool | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]: ...
