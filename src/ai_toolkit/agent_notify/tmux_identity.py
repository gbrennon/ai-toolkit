from dataclasses import dataclass


@dataclass(frozen=True)
class TmuxIdentity:
    """Identify the tmux window that owns an agent process."""

    session_name: str
    window_index: str
    window_name: str
