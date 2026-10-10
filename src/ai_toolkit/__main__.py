"""Executable module entry point for python -m ai_toolkit."""

from .cli import dispatch

if __name__ == "__main__":
    raise SystemExit(dispatch())
