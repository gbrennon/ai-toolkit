from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from ai_toolkit.cli import COMMANDS, dispatch


def _expected_subcommands_from_pyproject() -> set[str]:
    import tomllib

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    scripts: dict[str, str] = data.get("project", {}).get("scripts", {})
    # All scripts except ai-toolkit itself should be available as subcommands
    return {name for name in scripts if name != "ai-toolkit"}


def test_dispatcher_covers_every_pyproject_script() -> None:
    expected = _expected_subcommands_from_pyproject()
    assert set(COMMANDS.keys()) == expected


def test_help_prints_all_subcommands() -> None:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        status = dispatch(["--help"])
    assert status == 0
    output = stdout.getvalue()
    for name in COMMANDS:
        assert name in output


def test_no_args_prints_help() -> None:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        status = dispatch([])
    assert status == 0
    assert "Available commands:" in stdout.getvalue()


def test_unknown_subcommand_exits_with_error() -> None:
    stderr = io.StringIO()
    stdout = io.StringIO()
    with redirect_stderr(stderr), redirect_stdout(stdout):
        status = dispatch(["non-existent-subcommand"])
    assert status == 2
    assert "unknown command 'non-existent-subcommand'" in stderr.getvalue()


@pytest.mark.parametrize("command_name", sorted(COMMANDS.keys()))
def test_each_command_is_importable_and_callable(command_name: str) -> None:
    import importlib

    module_name, func_name = COMMANDS[command_name]
    module = importlib.import_module(module_name)
    assert hasattr(module, func_name), f"{command_name}: missing {func_name}"
    func = getattr(module, func_name)
    assert callable(func), f"{command_name}: {func_name} is not callable"


def test_dispatch_forwards_to_subcommand_help() -> None:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        status = dispatch(["install-agent-rules", "--help"])
    assert status == 0
    assert "install-agent-rules" in stdout.getvalue() or "usage" in stdout.getvalue().lower()


def test_dispatch_forwards_to_forge_detect() -> None:
    # forge-detect is harmless and prints detected forge
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        status = dispatch(["forge-detect"])
    assert status == 0
