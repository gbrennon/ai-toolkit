import json
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "hook-circuit-breaker.py"


def run_breaker(
    state_path: Path,
    action: str,
    *,
    session: str = "session-1",
    cwd: str = "/repo",
    path: str = "src/app.py",
    threshold: int = 3,
) -> subprocess.CompletedProcess[str]:
    environment = {
        **os.environ,
        "AI_TOOLKIT_CIRCUIT_BREAKER_STATE": str(state_path),
        "AI_TOOLKIT_CIRCUIT_BREAKER_THRESHOLD": str(threshold),
    }
    return subprocess.run(
        [
            str(SCRIPT),
            action,
            "--session",
            session,
            "--cwd",
            cwd,
            "--path",
            path,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def test_failure_opens_after_threshold_and_emits_terminal_json(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"

    first = run_breaker(state_path, "failure")
    second = run_breaker(state_path, "failure")
    terminal = run_breaker(state_path, "failure")

    assert first.returncode == 0
    assert second.returncode == 0
    assert terminal.returncode == 2
    payload = json.loads(terminal.stderr)
    assert payload["type"] == "circuit_breaker_open"
    assert payload["status"] == "terminal"
    assert payload["failures"] == 3
    assert payload["action"] == "read_file_again_or_request_help"


def test_success_resets_failures_for_target(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    run_breaker(state_path, "failure")
    run_breaker(state_path, "failure")
    reset = run_breaker(state_path, "success")
    next_failure = run_breaker(state_path, "failure")

    assert reset.returncode == 0
    assert next_failure.returncode == 0


def test_explicit_reset_reopens_circuit_for_attempts(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    for _ in range(3):
        run_breaker(state_path, "failure")

    reset = run_breaker(state_path, "reset")
    next_failure = run_breaker(state_path, "failure")

    assert reset.returncode == 0
    assert next_failure.returncode == 0


def test_open_circuit_blocks_before_next_attempt(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    for _ in range(3):
        run_breaker(state_path, "failure")

    blocked = run_breaker(state_path, "before")

    assert blocked.returncode == 2
    payload = json.loads(blocked.stderr)
    assert payload["type"] == "circuit_breaker_open"
    assert payload["failures"] == 3


def test_different_sessions_have_independent_circuits(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"

    for _ in range(3):
        run_breaker(state_path, "failure", session="session-1")

    other_session = run_breaker(state_path, "before", session="session-2")

    assert other_session.returncode == 0
