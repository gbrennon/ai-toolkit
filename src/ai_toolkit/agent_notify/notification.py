from dataclasses import dataclass
from pathlib import Path

from ai_toolkit.agent_notify.tmux_identity import TmuxIdentity


@dataclass(frozen=True)
class Notification:
    """Describe one agent lifecycle notification."""

    agent: str
    event: str
    cwd: Path
    identity: TmuxIdentity
    message: str
