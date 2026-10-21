from __future__ import annotations

import importlib
import inspect
import io
import tomllib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

import ai_toolkit
from ai_toolkit.cli import COMMANDS, ToolkitCli, dispatch, main


class TestCliDispatcher:
    def _expected_subcommands_from_pyproject(self) -> set[str]:
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        scripts: dict[str, str] = data.get("project", {}).get("scripts", {})
        return {name for name in scripts if name != "ai-toolkit"}

    def _fake_forge(self) -> str:
        return "codeberg"

    def test_exported_entrypoints_are_bound_methods(self) -> None:
        assert inspect.ismethod(dispatch)
        assert inspect.ismethod(main)
        assert inspect.ismethod(ai_toolkit.main)
        assert isinstance(dispatch.__self__, ToolkitCli)

    def test_dispatcher_covers_every_pyproject_script_and_internal_commands(
        self,
    ) -> None:
        expected = self._expected_subcommands_from_pyproject() | {"agent-registry"}
        assert set(COMMANDS.keys()) == expected

    def test_help_prints_all_subcommands(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = dispatch(["--help"])
        assert status == 0
        output = stdout.getvalue()
        for name in COMMANDS:
            assert name in output

    def test_no_args_prints_help(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = dispatch([])
        assert status == 0
        assert "Available commands:" in stdout.getvalue()

    def test_unknown_subcommand_exits_with_error(self) -> None:
        stderr = io.StringIO()
        stdout = io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(stdout):
            status = dispatch(["non-existent-subcommand"])
        assert status == 2
        assert "unknown command 'non-existent-subcommand'" in stderr.getvalue()

    @pytest.mark.parametrize("command_name", sorted(COMMANDS.keys()))
    def test_each_command_is_importable_and_callable(self, command_name: str) -> None:
        module_name, func_name = COMMANDS[command_name]
        module = importlib.import_module(module_name)
        assert hasattr(module, func_name), f"{command_name}: missing {func_name}"
        func = getattr(module, func_name)
        assert callable(func), f"{command_name}: {func_name} is not callable"

    def test_dispatch_forwards_to_subcommand_help(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = dispatch(["install-agent-rules", "--help"])
        assert status == 0
        assert "install-agent-rules" in stdout.getvalue() or "usage" in stdout.getvalue().lower()

    def test_dispatch_forwards_to_forge_detect(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("ai_toolkit.forge.detect.detect_forge", self._fake_forge)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = dispatch(["forge-detect"])
        assert status == 0
        assert stdout.getvalue().strip() == "codeberg"
