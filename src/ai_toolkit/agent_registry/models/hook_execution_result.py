from dataclasses import dataclass

from ._json import JsonValue


@dataclass(frozen=True, slots=True)
class HookExecutionResult:
    """Immutable outcome returned after one hook invocation."""

    hook_id: str
    outcome: str
    returncode: int | None
    blocked: bool
    duration: float
    stdout: str
    stderr: str

    def to_json(self) -> dict[str, JsonValue]:
        """Return the sanitized execution outcome."""
        return {
            "hookId": self.hook_id,
            "outcome": self.outcome,
            "returncode": self.returncode,
            "blocked": self.blocked,
            "duration": self.duration,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }
