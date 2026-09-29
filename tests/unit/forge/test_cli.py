import pytest

from ai_toolkit.forge.cli import (
    ForgeCliUnavailable,
    forge_cli_for_remote,
    resolve_forge_cli,
)


def test_github_resolves_to_gh(monkeypatch):
    monkeypatch.setattr("ai_toolkit.forge.cli.shutil.which", lambda name: "/bin/" + name)
    assert resolve_forge_cli("github") == "gh"


def test_codeberg_resolves_to_fj(monkeypatch):
    monkeypatch.setattr("ai_toolkit.forge.cli.shutil.which", lambda name: "/bin/" + name)
    assert resolve_forge_cli("codeberg") == "fj"


def test_missing_cli_is_actionable(monkeypatch):
    monkeypatch.setattr("ai_toolkit.forge.cli.shutil.which", lambda _: None)
    with pytest.raises(ForgeCliUnavailable) as error:
        resolve_forge_cli("github")

    message = str(error.value)
    assert "Install gh" in message
    assert "gh auth login" in message
    assert "rerun the command" in message


def test_forgejo_remote_resolves_to_fj(monkeypatch):
    monkeypatch.setattr("ai_toolkit.forge.cli.detect_forge", lambda: "forgejo")
    monkeypatch.setattr("ai_toolkit.forge.cli.shutil.which", lambda name: "/bin/" + name)

    assert forge_cli_for_remote() == "fj"


def test_unknown_forge_is_rejected(monkeypatch):
    monkeypatch.setattr("ai_toolkit.forge.cli.shutil.which", lambda name: "/bin/" + name)
    with pytest.raises(ValueError, match="Unsupported forge"):
        resolve_forge_cli("bitbucket")
