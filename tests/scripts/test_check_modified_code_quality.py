import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

WRAPPER = Path(__file__).parents[2] / "scripts" / "check-modified-code-quality.sh"


def run_wrapper(
    event: Mapping[str, object],
    tmp_path: Path,
    fake_checker_output: str = "",
    checker_status: int = 0,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    checker = bin_dir / "check-code-quality"
    checker.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$@\" > args.txt\n"
        + f"printf '%s' {json.dumps(fake_checker_output)}\n"
        + f"exit {checker_status}\n",
        encoding="utf-8",
    )
    checker.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "AI_TOOLKIT_CIRCUIT_BREAKER_STATE": str(tmp_path / "breaker-state.json"),
        "AI_TOOLKIT_CIRCUIT_BREAKER_THRESHOLD": "3",
        "AI_TOOLKIT_CIRCUIT_BREAKER_COMMAND": str(
            Path(__file__).parents[2] / "scripts" / "hook-circuit-breaker.py"
        ),
    }
    return subprocess.run(
        [str(WRAPPER)],
        cwd=tmp_path,
        input=json.dumps(event),
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def test_passed_check_receives_only_modified_path(tmp_path: Path) -> None:
    event = {"tool_name": "Write", "tool_input": {"path": "tests/app.py"}}

    result = run_wrapper(event, tmp_path, fake_checker_output="passed")

    assert result.returncode == 0
    assert result.stdout == ""
    assert (tmp_path / "args.txt").read_text(encoding="utf-8") == "tests/app.py\n"


def test_failed_check_reports_violations_as_feedback(tmp_path: Path) -> None:
    event = {"tool_name": "Write", "tool_input": {"path": "tests/app.py"}}

    result = run_wrapper(
        event,
        tmp_path,
        fake_checker_output="violation",
        checker_status=1,
    )

    assert result.returncode == 0
    assert "violation" in result.stdout
    assert result.stderr == ""


def test_failed_check_opens_circuit_after_repeated_attempts(tmp_path: Path) -> None:
    event = {
        "tool_name": "Write",
        "session_id": "session-1",
        "tool_input": {"path": "tests/app.py"},
    }

    first = run_wrapper(event, tmp_path, checker_status=1)
    second = run_wrapper(event, tmp_path, checker_status=1)
    terminal = run_wrapper(event, tmp_path, checker_status=1)

    assert first.returncode == 0
    assert second.returncode == 0
    assert terminal.returncode == 0
    assert "circuit_breaker_open" in terminal.stdout
    assert '"continue": false' in terminal.stdout
    assert terminal.stderr == ""


def test_missing_path_skips_quality_check(tmp_path: Path) -> None:
    result = run_wrapper({"tool_input": {}}, tmp_path)

    assert result.returncode == 0
    assert result.stdout == ""
    assert not (tmp_path / "args.txt").exists()


@pytest.mark.parametrize(
    ("tool_name", "path", "checker_called"),
    [
        ("Read", "README.md", False),
        ("Other", "README.md", False),
        ("Write", "README.md", True),
        ("Edit", "module.py", True),
        ("Edit", "module.rs", True),
    ],
)
def test_quality_check_runs_only_for_edits(
    tool_name: str,
    path: str,
    checker_called: bool,
    tmp_path: Path,
) -> None:
    event = {"tool_name": tool_name, "tool_input": {"path": path}}

    result = run_wrapper(event, tmp_path)

    assert result.returncode == 0
    assert (tmp_path / "args.txt").exists() is checker_called
    if checker_called:
        assert (tmp_path / "args.txt").read_text(encoding="utf-8") == f"{path}\n"
