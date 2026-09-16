import argparse
import sys

from ai_toolkit.install_hooks.installers.hook_installer_factory import (
    HookInstallerFactory,
)

AGENTS = ("pi", "opencode", "cline", "omp", "all")


def install(agent: str) -> int:
    """Install quality hooks for the selected agent(s), returning process exit code."""
    print(f"\nInstalling hooks for: {agent}")
    ok = True
    for installer in HookInstallerFactory.create(agent):
        ok = installer.install() and ok
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install quality hooks per agent")
    parser.add_argument(
        "--agent", choices=AGENTS, default="all", help="which agent to configure"
    )
    args = parser.parse_args(argv)
    return install(args.agent)


if __name__ == "__main__":
    sys.exit(main())
