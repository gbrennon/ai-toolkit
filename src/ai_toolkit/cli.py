"""Command-line dispatcher for all ai-toolkit tools."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence

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


def _help() -> None:
    lines = [
        "usage: ai-toolkit <command> [args...]",
        "",
        "Available commands:",
    ]
    for name in sorted(COMMANDS):
        lines.append(f"  {name}")
    print("\n".join(lines))


def dispatch(argv: Sequence[str] | None = None) -> int:
    """Dispatch argv to the target tool callable."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help", "help"):
        _help()
        return 0

    command = args[0]
    rest = args[1:]
    target = COMMANDS.get(command)
    if target is None:
        print(f"ai-toolkit: unknown command '{command}'", file=sys.stderr)
        _help()
        return 2

    module_name, func_name = target
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)

    # Forward remaining args via sys.argv so standard-library argparse/typer work
    original_argv = sys.argv
    sys.argv = [f"ai-toolkit {command}", *rest]
    try:
        try:
            result = func(rest)
        except TypeError:
            result = func()
    except SystemExit as error:
        code = error.code
        return code if isinstance(code, int) else 0 if code is None else 1
    finally:
        sys.argv = original_argv

    return result if isinstance(result, int) else 0


def main() -> None:
    """Entry point for the ai-toolkit console script."""
    raise SystemExit(dispatch())
