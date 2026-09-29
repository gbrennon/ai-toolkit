import pytest

from ai_toolkit.forge.cli import ForgeCliUnavailable, resolve_forge_cli


def test_github_resolves_to_gh(monkeypatch):
    monkeypatch.setattr("ai_toolkit.forge.cli.shutil.which", lambda name: "/bin/" + name)
    assert resolve_forge_cli("github") == "gh"


def test_codeberg_resolves_to_fj(monkeypatch):
    monkeypatch.setattr("ai_toolkit.forge.cli.shutil.which", lambda name: "/bin/" + name)
    assert resolve_forge_cli("codeberg") == "fj"


def test_missing_cli_is_actionable(monkeypatch):
    monkeypatch.setattr("ai_toolkit.forge.cli.shutil.which", lambda _: None)
    with pytest.raises(ForgeCliUnavailable, match="gh"):
        resolve_forge_cli("github")


def test_unknown_forge_is_rejected(monkeypatch):
    monkeypatch.setattr("ai_toolkit.forge.cli.shutil.which", lambda name: "/bin/" + name)
    with pytest.raises(ValueError, match="Unsupported forge"):
        resolve_forge_cli("bitbucket")
