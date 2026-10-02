from __future__ import annotations

import shutil
from collections.abc import Callable
from urllib.parse import urlparse

from ai_toolkit.forge.api import classify_forge
from ai_toolkit.forge.detect import detect_forge


Which = Callable[[str], str | None]


CLI_BY_FORGE = {
    "github": "gh",
    "codeberg": "fj",
    "gitea": "fj",
    "forgejo": "fj",
}


class ForgeCliUnavailable(RuntimeError):
    """The forge CLI required by the repository remote is unavailable."""


def _remote_host(remote_url: str) -> str:
    parsed = urlparse(remote_url)
    if parsed.hostname:
        return parsed.hostname

    host = remote_url.split("@", 1)[-1].split(":", 1)[0].split("/", 1)[0]
    if not host:
        raise ValueError(f"Could not determine forge host from remote: {remote_url}")
    return host


def _cli_for_forge(forge: str | None) -> str:
    if forge not in CLI_BY_FORGE:
        raise ValueError(f"Unsupported forge: {forge or 'no git remote'}")
    return CLI_BY_FORGE[forge]


def _require_cli(cli: str, forge: str | None, which: Which) -> None:
    if which(cli) is None:
        raise ForgeCliUnavailable(
            f"{cli} is required for {forge} repositories but is not installed. "
            f"Install {cli}, authenticate with `{cli} auth login`, and rerun the command."
        )


def resolve_forge_cli(
    forge: str | None = None,
    *,
    which: Which | None = None,
) -> str:
    selected_forge = forge or detect_forge()
    cli = _cli_for_forge(selected_forge)
    find_cli = shutil.which if which is None else which
    _require_cli(cli, selected_forge, find_cli)
    return cli


def resolve_forge_cli_from_remote(
    remote_url: str,
    *,
    which: Which | None = None,
) -> str:
    """Resolve a forge CLI directly from a git remote URL.

    This path is intentionally independent of the ``forge-detect`` executable so
    callers operating in another repository can still select the correct CLI.
    """

    forge = classify_forge(_remote_host(remote_url))
    return resolve_forge_cli(forge, which=which)


def forge_cli_for_remote() -> str:
    return resolve_forge_cli()
