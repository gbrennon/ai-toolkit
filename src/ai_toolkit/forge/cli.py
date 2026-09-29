from __future__ import annotations

import shutil

from ai_toolkit.forge.detect import detect_forge


CLI_BY_FORGE = {
    "github": "gh",
    "codeberg": "fj",
    "gitea": "fj",
    "forgejo": "fj",
}


class ForgeCliUnavailable(RuntimeError):
    """The forge CLI required by the repository remote is unavailable."""


def resolve_forge_cli(forge: str | None = None) -> str:
    selected_forge = forge or detect_forge()
    if selected_forge not in CLI_BY_FORGE:
        raise ValueError(f"Unsupported forge: {selected_forge or 'no git remote'}")

    cli = CLI_BY_FORGE[selected_forge]
    if shutil.which(cli) is None:
        raise ForgeCliUnavailable(
            f"{cli} is required for {selected_forge} repositories but is not installed. "
            f"Install {cli}, authenticate with `{cli} auth login`, and rerun the command."
        )
    return cli


def forge_cli_for_remote() -> str:
    return resolve_forge_cli()
