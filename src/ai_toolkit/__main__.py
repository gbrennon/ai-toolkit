"""Executable module entry point for python -m ai_toolkit."""

from __future__ import annotations

from .cli import ToolkitCli


class AiToolkitMain:
    """Module execution runner for python -m ai_toolkit."""

    def __init__(self, cli: ToolkitCli | None = None) -> None:
        self._cli = ToolkitCli() if cli is None else cli

    def run(self) -> None:
        """Execute the CLI dispatcher and exit with its status code."""
        self._cli.main()


if __name__ == "__main__":
    AiToolkitMain().run()
