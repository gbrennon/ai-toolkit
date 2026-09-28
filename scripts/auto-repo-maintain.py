"""Watch PR event files and trigger repository maintenance."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Final, TypedDict


class PullRequestEvent(TypedDict, total=False):
    """Describe the pull request fields used by the maintenance listener."""

    number: int
    html_url: str


class EventPayload(TypedDict, total=False):
    """Describe an event payload containing pull request metadata."""

    pull_request: PullRequestEvent


POLL_INTERVAL: Final[int] = int(os.getenv("POLL_INTERVAL", "30"))
EVENTS_DIR: Final[Path] = Path(os.getenv("EVENTS_DIR", ".agent-events"))
REPO_OWNER: Final[str] = os.getenv("REPO_OWNER", "owner")
REPO_NAME: Final[str] = os.getenv("REPO_NAME", "repo")


def is_event_file(path: Path) -> bool:
    """Return whether a path names a PR-opened event file."""
    return all(
        (
            path.is_file(),
            path.name.startswith("pr-"),
            "opened" in path.name,
            path.suffix == ".json",
        )
    )


def event_files() -> list[Path]:
    """Return pending PR-opened event files in stable order."""
    if not EVENTS_DIR.is_dir():
        return []
    return sorted(path for path in EVENTS_DIR.iterdir() if is_event_file(path))


def read_event(event_path: Path) -> tuple[int, str] | None:
    """Return the pull request number and URL from an event file."""
    try:
        payload = json.loads(event_path.read_text())
        pull_request = payload["pull_request"]
        number = int(pull_request["number"])
        url = str(pull_request.get("html_url", ""))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
        return None
    if not url:
        url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/pull/{number}"
    return number, url


def run_maintenance(pr_url: str) -> bool:
    """Run the repository maintenance command for a pull request."""
    command: list[str] = [
        "uv",
        "run",
        "--with",
        "typer",
        "python",
        "-m",
        "src.cli.repo_maintenance",
        pr_url,
        "--auto-update",
        "--cache-ttl=300s",
    ]
    result = subprocess.run(command, check=False)
    return result.returncode == 0


def process_event(event_path: Path) -> bool:
    """Process one event and remove it only after successful maintenance."""
    event = read_event(event_path)
    if event is None:
        print(f"[AUTONOMOUS] Invalid event: {event_path}")
        return False
    number, url = event
    print(f"[AUTONOMOUS] Detected PR #{number}: {url}")
    if not run_maintenance(url):
        print(f"[AUTONOMOUS] Maintenance failed for PR #{number}")
        return False
    event_path.unlink()
    print(f"[AUTONOMOUS] Maintenance completed for PR #{number}")
    return True


def main() -> None:
    """Continuously process pending pull request events."""
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        pending_events = event_files()
        if pending_events:
            process_event(pending_events[0])
        else:
            print("[AUTONOMOUS] No pending events")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
