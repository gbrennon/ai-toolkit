"""Command-line dispatcher for all ai-toolkit tools."""

from __future__ import annotations

import importlib
import inspect
import sys
from collections.abc import Callable, Sequence


class ToolkitCli:
    """Route ai-toolkit subcommands to their registered tool entry points."""

    COMMANDS: dict[str, tuple[str, str]] = {
        "agent-registry": ("ai_toolkit.agent_registry.cli", "main"),
        "install-skills": ("ai_toolkit.install_skills.main", "main"),
        "install-mcp-servers": ("ai_toolkit.install_mcp_servers.main", "main"),
        "install-pi-config": ("ai_toolkit.install_pi_config.main", "main"),
        "install-agent-rules": ("ai_toolkit.install_agent_rules.main", "main"),
        "install-omp-commands": ("ai_toolkit.install_omp_commands.main", "main"),
        "install-provider-blocks": ("ai_toolkit.install_provider_blocks.main", "main"),
        "install-hooks": ("ai_toolkit.install_hooks.main", "main"),
        "fetch-pr-review": ("ai_toolkit.fetch_pr_review.main", "main"),
        "forge-issue": ("ai_toolkit.forge_issue.main", "main"),
        "forge-detect": ("ai_toolkit.forge.detect", "main"),
        "repo-maintenance": ("ai_toolkit.repo_maintenance", "main"),
        "agent-hook-pr-review": ("ai_toolkit.agent_hook_pr_review.main", "main"),
        "agent-notify": ("ai_toolkit.agent_notify.main", "main"),
    }

    def _help(self) -> None:
        lines = [
            "usage: ai-toolkit <command> [args...]",
            "",
            "Available commands:",
        ]
        for name in sorted(self.COMMANDS):
            lines.append(f"  {name}")
        print("\n".join(lines))

    def _normalize_args(self, argv: Sequence[str] | None) -> list[str]:
        return list(sys.argv[1:] if argv is None else argv)

    def _accepts_arguments(self, func: Callable[..., object]) -> bool:
        return bool(inspect.signature(func).parameters)

    def _call_target(
        self,
        func: Callable[..., object],
        rest: list[str],
    ) -> object:
        if self._accepts_arguments(func):
            return func(rest)
        return func()

    def _exit_code(self, code: object) -> int:
        if isinstance(code, int):
            return code
        return 0 if code is None else 1

    def _invoke(
        self,
        command: str,
        rest: list[str],
        target: tuple[str, str],
    ) -> int:
        module_name, func_name = target
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
        original_argv = sys.argv
        sys.argv = [f"ai-toolkit {command}", *rest]
        try:
            result = self._call_target(func, rest)
        except SystemExit as error:
            return self._exit_code(error.code)
        finally:
            sys.argv = original_argv
        return result if isinstance(result, int) else 0

    def dispatch(self, argv: Sequence[str] | None = None) -> int:
        """Dispatch argv to the target tool callable."""
        args = self._normalize_args(argv)
        if not args or args[0] in ("-h", "--help", "help"):
            self._help()
            return 0
        command = args[0]
        target = self.COMMANDS.get(command)
        if target is None:
            print(f"ai-toolkit: unknown command '{command}'", file=sys.stderr)
            self._help()
            return 2
        return self._invoke(command, args[1:], target)

    def main(self) -> None:
        """Entry point for the ai-toolkit console script."""
        raise SystemExit(self.dispatch())


_CLI = ToolkitCli()
COMMANDS = ToolkitCli.COMMANDS
dispatch = _CLI.dispatch
main = _CLI.main
