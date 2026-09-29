import json
import sys

from ai_toolkit.forge.api import (
    detect_forge,
    get_main_remote,
    get_remote_url,
)


def _cli_mode() -> int:
    from ai_toolkit.forge.cli import ForgeCliUnavailable, forge_cli_for_remote

    try:
        print(forge_cli_for_remote())
    except (ForgeCliUnavailable, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def _detect_mode() -> int:
    forge = detect_forge()
    if forge is None:
        print("No git remote found", file=sys.stderr)
        return 1

    remote = get_main_remote()
    url = get_remote_url()
    if "--json" in sys.argv:
        print(json.dumps({"forge": forge, "remote": remote, "url": url}))
    else:
        print(forge)
    return 0


def main() -> int:
    if "--help" in sys.argv or "-h" in sys.argv:
        print("usage: forge-detect [--json | --cli]")
        return 0
    if "--cli" in sys.argv:
        return _cli_mode()
    return _detect_mode()


if __name__ == "__main__":
    sys.exit(main())
