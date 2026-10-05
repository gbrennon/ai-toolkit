"""
PR Opened Hook

Executes repo-maintenance loop when a new pull request is opened.
Uses direct API calls with caching. Works even with dirty state.
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Optional, List

class PROpenedHook:
    """
    Detects when a new PR is opened and triggers maintenance loop.
    Works even if .agent-events is missing or ignored.
    """

    def __init__(self, events_dir: Path = Path(".agent-events"), cache_ttl: int = 300):
        self.events_dir = events_dir
        self.cache_ttl = cache_ttl

    def _ensure_events_directory_exists(self) -> bool:
        """
        Ensure .agent-events directory exists.
        Creates it if missing, but doesn't fail on permission errors.
        """
        try:
            if not self.events_dir.exists():
                self.events_dir.mkdir(parents=True, exist_ok=True)
                print(f"[HOOK] Created events directory: {self.events_dir}")
            elif not os.access(self.events_dir, os.R_OK | os.W_OK):
                print(f"[HOOK] Warning: Cannot access events directory: {self.events_dir} (read/write denied)")
                return False
            return True
        except Exception as e:
            print(f"[HOOK] Failed to ensure events dir: {e}")
            return False

    def detect(self) -> bool:
        """
        Check if any unprocessed PR opened event exists.
        Returns True if one found.
        """
        try:
            # Ensure the directory exists before scanning
            if not self._ensure_events_directory_exists():
                return False

            # Now scan files safely
            for file in self.events_dir.iterdir():
                if not self._is_valid_event_file(file):
                    continue
                return True

            return False
        except Exception as e:
            print(f"[HOOK] Failed to detect PR event: {e}")
            return False

    def run(self) -> bool:
        """Run maintenance for the first valid pull-request event."""
        try:
            for file in self.events_dir.iterdir():
                if not self._is_valid_event_file(file):
                    continue
                result = self._process_event(file)
                if result is not None:
                    return result
            return False
        except Exception as error:
            print(f"[HOOK] Critical failure running hook: {error}")
            return False

    def _process_event(self, file: Path) -> bool | None:
        pr_number, pr_url, branch = self._parse_event_file(file)
        if pr_number is None or pr_url is None:
            return None
        print(f"[HOOK] Detected PR #{pr_number} at {pr_url} on branch {branch}")
        self._report_worktree_state()
        command = f'uv run repo-maintenance "{pr_url}" --auto-update --cache-ttl={self.cache_ttl}'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return self._finish_event(file, pr_number, result)

    def _report_worktree_state(self) -> None:
        message = "Working tree is dirty. Proceeding anyway." if self._is_dirty_state() else "Working tree is clean"
        print(f"[HOOK] {message}")

    def _finish_event(self, file: Path, pr_number: int, result: subprocess.CompletedProcess[str]) -> bool:
        if result.returncode != 0:
            print(f"[HOOK] Maintenance failed: {result.stderr.strip() or 'Unknown'}")
            return False
        print(f"[HOOK] Maintenance completed successfully for PR #{pr_number}")
        file.unlink()
        return True

    def _is_valid_event_file(self, file: Path) -> bool:
        """
        Check if a file matches the expected PR opened event pattern.
        """
        return (file.is_file() and
                file.name.startswith("pr-") and
                "opened" in file.name and
                file.suffix == ".json")

    def _parse_event_file(self, file: Path) -> tuple[Optional[int], Optional[str], Optional[str]]:
        """Parse a JSON event file into pull-request identifiers."""
        try:
            with open(file) as event_file:
                data = json.load(event_file)
            return self._parse_event_payload(data)
        except Exception as error:
            print(f"[HOOK] Failed to parse event file {file}: {error}")
            return None, None, None

    def _parse_event_payload(
        self,
        data: object,
    ) -> tuple[Optional[int], Optional[str], Optional[str]]:
        if not isinstance(data, dict):
            return None, None, None
        pull_request = data.get("pull_request")
        if not isinstance(pull_request, dict):
            return None, None, None
        return self._parse_pull_request(pull_request)

    def _parse_pull_request(
        self,
        pull_request: dict[object, object],
    ) -> tuple[Optional[int], Optional[str], Optional[str]]:
        pr_num = pull_request.get("number")
        pr_url = pull_request.get("html_url")
        head = pull_request.get("head")
        if not isinstance(pr_num, (int, str)) or not isinstance(pr_url, str):
            return None, None, None
        if not isinstance(head, dict) or not isinstance(head.get("ref"), str):
            return None, None, None
        return int(pr_num), pr_url, head["ref"]

    def _is_dirty_state(self) -> bool:
        """
        Check if git working tree has uncommitted changes.
        Returns True if dirty.
        """
        try:
            result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            return len(result.stdout.strip()) > 0
        except Exception:
            return False
