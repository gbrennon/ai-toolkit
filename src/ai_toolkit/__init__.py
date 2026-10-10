"""AI Toolkit."""

__version__ = "0.1.0"


def main() -> None:
    """Run the toolkit command-line entry point."""
    from .cli import dispatch

    raise SystemExit(dispatch())