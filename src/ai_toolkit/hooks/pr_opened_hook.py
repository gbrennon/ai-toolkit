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
        self.processed_events: set[str] = set()

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
                if str(file) in self.processed_events:
                    continue
                return True

            return False
        except Exception as e:
            print(f"[HOOK] Failed to detect PR event: {e}")
            return False

    def run(self) -> bool:
        """
        Run maintenance loop for first detected PR.
        Returns True on success.
        """
        try:
            # Find first valid event file
            for file in self.events_dir.iterdir():
                if not self._is_valid_event_file(file):
                    continue
                if str(file) in self.processed_events:
                    continue

                # Process it
                pr_number, pr_url, branch = self._parse_event_file(file)
                if not pr_number or not pr_url:
                    continue

                # Report status
                print(f"[HOOK] 🟢 Detected PR #{pr_number} at {pr_url} on branch {branch}")
                if self._is_dirty_state():
                    print(f"[HOOK] ⚠️ Working tree is dirty. Proceeding anyway.")
                else:
                    print(f"[HOOK] ✅ Working tree is clean")

                # Trigger maintenance
                cmd = f"uv run repo-maintenance \"{pr_url}\" --auto-update --cache-ttl={self.cache_ttl}"  # noqa: E501
                print(f"[HOOK] 🔁 Running: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    print(f"[HOOK] ✅ Maintenance completed successfully for PR #{pr_number}")
                    self.processed_events.add(str(file))
                    file.unlink()
                    print(f"[HOOK] 💀 Removed event file: {file.name}")
                    return True
                else:
                    error_msg = result.stderr.strip() or 'Unknown'
                    print(f"[HOOK] ❌ Error during maintenance: {error_msg}")
                    return False

            return False
        except Exception as e:
            print(f"[HOOK] Critical failure running hook: {e}")
            return False

    def _is_valid_event_file(self, file: Path) -> bool:
        """
        Check if a file matches the expected PR opened event pattern.
        """
        return (file.is_file() and
                file.name.startswith("pr-") and
                "opened" in file.name and
                file.suffix == ".json")

    def _parse_event_file(self, file: Path) -> tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Parse JSON content to extract PR number, URL, and branch.
        Returns (number, url, branch) or (None, None, None) on failure.
        """
        try:
            with open(file) as f:
                data = json.load(f)

            pr_data = data.get("pull_request", {})
            if not isinstance(pr_data, dict):
                return None, None, None

            pr_num = pr_data.get("number")
            pr_url = pr_data.get("html_url")
            head_ref = pr_data.get("head", {}).get("ref")

            return int(pr_num), str(pr_url), str(head_ref)
        except Exception as e:
            print(f"[HOOK] Failed to parse event file {file}: {e}")
            return None, None, None

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
