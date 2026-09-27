#!/usr/bin/env python3

import argparse
import fcntl
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Final

DEFAULT_THRESHOLD: Final[int] = 3
DEFAULT_STATE_RELATIVE_PATH: Final[Path] = (
    Path("ai-toolkit") / "hook-circuit-breaker.json"
)


def state_path() -> Path:
    """Return the configured persistent state path."""
    configured_path = os.environ.get("AI_TOOLKIT_CIRCUIT_BREAKER_STATE")
    if configured_path:
        return Path(configured_path)
    state_home = os.environ.get(
        "XDG_STATE_HOME", str(Path.home() / ".local" / "state")
    )
    return Path(state_home) / DEFAULT_STATE_RELATIVE_PATH


def threshold() -> int:
    """Return the configured failure threshold."""
    configured_threshold = os.environ.get("AI_TOOLKIT_CIRCUIT_BREAKER_THRESHOLD")
    if configured_threshold is None:
        return DEFAULT_THRESHOLD
    value = int(configured_threshold)
    if value < 1:
        raise ValueError("AI_TOOLKIT_CIRCUIT_BREAKER_THRESHOLD must be positive")
    return value


def target_key(session: str, cwd: str, path: str) -> str:
    """Return a stable key for one agent session target."""
    return json.dumps([session, cwd, path], separators=(",", ":"))


def load_state() -> dict[str, int]:
    """Load state, treating missing or malformed state as empty."""
    path = state_path()
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {key: count for key, count in value.items() if isinstance(count, int)}


def save_state(state: dict[str, int]) -> None:
    """Atomically persist circuit state."""
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        json.dump(state, temporary, sort_keys=True)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.chmod(0o600)
    temporary_path.replace(path)


def terminal_payload(session: str, cwd: str, path: str, failures: int) -> str:
    """Return the machine-readable terminal circuit-breaker result."""
    return json.dumps(
        {
            "type": "circuit_breaker_open",
            "status": "terminal",
            "session": session,
            "cwd": cwd,
            "path": path,
            "failures": failures,
            "action": "read_file_again_or_request_help",
        },
        sort_keys=True,
    )


def run(action: str, session: str, cwd: str, path: str) -> int:
    """Apply one circuit-breaker action and return its hook exit status."""
    key = target_key(session, cwd, path)
    state_file = state_path()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_file.with_suffix(state_file.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = load_state()
        failures = state.get(key, 0)
        if action in ("success", "reset"):
            state.pop(key, None)
            save_state(state)
            return 0
        if action == "failure":
            failures += 1
            state[key] = failures
            save_state(state)
        if failures >= threshold():
            print(terminal_payload(session, cwd, path, failures), file=sys.stderr)
            return 2
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the circuit-breaker command arguments."""
    parser = argparse.ArgumentParser(description="Guard agent hook retry loops")
    parser.add_argument("action", choices=("before", "success", "failure", "reset"))
    parser.add_argument("--session", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--path", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the circuit-breaker command."""
    try:
        args = parse_args(argv)
        return run(args.action, args.session, args.cwd, args.path)
    except (OSError, ValueError) as error:
        print(
            json.dumps(
                {
                    "type": "circuit_breaker_error",
                    "status": "fail_open",
                    "error": str(error),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
