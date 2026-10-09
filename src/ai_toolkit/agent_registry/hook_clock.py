from datetime import datetime
from typing import Protocol


class HookClock(Protocol):
    """Provide wall-clock and monotonic time to hook execution."""

    def now(self) -> datetime:
        """Return the current timestamp."""
        ...

    def monotonic(self) -> float:
        """Return a monotonic duration clock reading."""
        ...
