import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

WRAPPER = Path(__file__).parents[2] / "scripts" / "check-modified-code-quality.sh"


def run_wrapper(
    event: Mapping[str, object],
    tmp_path: Path,
    fake_checker_output: str = "",
    checker_status: int = 0,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    checker = bin_dir / "check-code-quality"
    checker.write_text(
        "printf '%s\\n' \"$@\" > args.txt\n"
        + f"printf '%s' {json.dumps(fake_checker_output)}\n"
        + f"exit {checker_status}\n",
        encoding="utf-8",
    )
    checker.chmod(0o755)
    environment = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
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
    event = {"tool_input": {"path": "tests/app.py"}}

    result = run_wrapper(event, tmp_path, fake_checker_output="passed")

    assert result.returncode == 0
    assert result.stdout == ""
    assert (tmp_path / "args.txt").read_text(encoding="utf-8") == "tests/app.py\n"


def test_failed_check_returns_checker_output(tmp_path: Path) -> None:
    event = {"tool_input": {"path": "tests/app.py"}}

    result = run_wrapper(
        event,
        tmp_path,
        fake_checker_output="violation",
        checker_status=1,
    )

    assert result.returncode == 1
    assert result.stdout == "violation\n"


def test_missing_path_skips_quality_check(tmp_path: Path) -> None:
    result = run_wrapper({"tool_input": {}}, tmp_path)

    assert result.returncode == 0
    assert result.stdout == ""
    assert not (tmp_path / "args.txt").exists()
