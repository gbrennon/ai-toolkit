"""AI Toolkit."""

from __future__ import annotations

from .cli import ToolkitCli

__version__ = "0.1.0"


class AiToolkitPackage:
    """Package-level entry point for AI Toolkit."""

    def __init__(self, cli: ToolkitCli | None = None) -> None:
        self._cli = ToolkitCli() if cli is None else cli

    def main(self) -> None:
        """Run the toolkit command-line entry point."""
        self._cli.main()


_PACKAGE = AiToolkitPackage()
main = _PACKAGE.main
