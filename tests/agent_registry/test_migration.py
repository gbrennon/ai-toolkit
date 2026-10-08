from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from ai_toolkit.agent_registry.audit import AuditEventStore
from ai_toolkit.agent_registry.errors import InvalidOperationError
from ai_toolkit.agent_registry.git_port import GitPort
from ai_toolkit.agent_registry.json_document_store import JsonDocumentStore
from ai_toolkit.agent_registry.models._json import JsonValue
from ai_toolkit.agent_registry.paths import RegistryPaths
from ai_toolkit.agent_registry.service import RegistryService


INSTANT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _agent(repository_id: str, remote: str) -> str:
    return "\n".join(
        [
            "---",
            "registrySchema: 1",
            f"repositoryId: {repository_id}",
            f"gitRemote: {remote}",
            "configVersion: 1",
            "lastReviewed: 2026-01-01T00:00:00Z",
            "---",
            "# AGENT.md",
            "",
            "## Scope",
            "Global policy.",
            "",
            "## Precedence",
            "Registry policy.",
            "",
            "## Repository identity",
            f"- Git remote: {remote}",
            "- Local path: /old/project",
            "",
            "## Required behavior",
            "Behavior.",
            "",
            "## Architecture and coding standards",
            "Standards.",
            "",
            "## Verification",
            "Verification.",
            "",
            "## Skills",
            "- No global skills selected.",
            "",
            "## Hooks",
            "- No global hooks selected.",
            "",
            "## Security and secrets",
            "No secrets.",
            "",
            "## Change policy",
            "Registry changes only.",
            "",
        ]
    )


def _git(root: Path, remote: str) -> SimpleNamespace:
    state = SimpleNamespace(root=root.resolve(), remote=remote)

    def resolve_worktree_root(_path: Path) -> Path:
        return state.root

    def canonical_remote(_path: Path) -> str:
        return "origin"

    def remote_url(_path: Path, _remote: str = "origin") -> str:
        return state.remote

    state.resolve_worktree_root = resolve_worktree_root
    state.canonical_remote = canonical_remote
    state.remote_url = remote_url
    return state


def _prepared(tmp_path: Path) -> tuple[RegistryPaths, Path, RegistryService]:
    paths = RegistryPaths(tmp_path / "registry")
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "AGENT.md").write_text(
        _agent("project", "https://example.test/acme/project"), encoding="utf-8"
    )
    (repository / "source.txt").write_bytes(b"repository bytes")
    service = RegistryService(
        paths,
        git=cast(
            GitPort,
            _git(repository, "https://example.test/acme/project.git"),
        ),
        clock=lambda: INSTANT,
    )
    service.initialize()
    service.register(repository, review=False)
    return paths, repository, service


def test_migrate_updates_remote_and_local_path_without_touching_repository(
    tmp_path: Path,
) -> None:
    paths, repository, service = _prepared(tmp_path)
    before = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    moved_path = (tmp_path / "moved-project").resolve()

    record = service.migrate(
        "project", "ssh://EXAMPLE.TEST/acme/project.git", moved_path
    )

    assert record.git_remote == "https://example.test/acme/project"
    assert record.local_path == moved_path
    assert json.loads(paths.registry_file.read_text())["repositories"][0][
        "localPath"
    ] == str(moved_path)
    content = paths.repository("project").agent_config.read_text()
    assert "gitRemote: https://example.test/acme/project" in content
    assert "- Git remote: https://example.test/acme/project" in content
    assert f"- Local path: {moved_path}" in content
    assert {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    } == before


def test_migrate_rejects_normalized_remote_and_active_path_collisions(
    tmp_path: Path,
) -> None:
    paths, repository, service = _prepared(tmp_path)
    second = tmp_path / "second"
    second.mkdir()
    (second / "AGENT.md").write_text(
        _agent("second", "https://example.test/other/second"), encoding="utf-8"
    )
    other_service = RegistryService(
        paths,
        git=cast(
            GitPort,
            _git(second, "https://example.test/other/second.git"),
        ),
        clock=lambda: INSTANT,
    )
    other_service.register(second, review=False)

    with pytest.raises(InvalidOperationError):
        service.migrate("project", "ssh://example.test/other/second.git", None)
    with pytest.raises(InvalidOperationError):
        service.migrate("project", None, second)

    assert paths.repository("project").metadata.is_file()
    assert repository.joinpath("source.txt").read_bytes() == b"repository bytes"


def test_migrate_backs_up_managed_files_before_change_and_records_audit_and_changelog(
    tmp_path: Path,
) -> None:
    paths, _, service = _prepared(tmp_path)
    old_agent = paths.repository("project").agent_config.read_bytes()
    old_metadata = paths.repository("project").metadata.read_bytes()

    service.migrate("project", "https://example.test/new/project.git", None)

    backup = paths.root / "backups" / "project"
    assert (backup / "AGENT.md").read_bytes() == old_agent
    assert (backup / "metadata.json").read_bytes() == old_metadata
    report = AuditEventStore(paths.repository("project").changes_audit).read()
    assert [event.operation for event in report.events] == ["migrate"]
    assert report.events[0].metadata["oldRemote"] == "https://example.test/acme/project"
    assert "project" in paths.changelog.read_text(encoding="utf-8")
    assert "migrate" in paths.changelog.read_text(encoding="utf-8")


def test_migrate_validates_result_and_preserves_omitted_values(tmp_path: Path) -> None:
    paths, repository, service = _prepared(tmp_path)
    original = service.migrate("project", None, None)

    assert original.git_remote == "https://example.test/acme/project"
    assert original.local_path == repository.resolve()
    assert (
        JsonDocumentStore().read(paths.repository("project").metadata)
        == original.to_json()
    )


def _managed_files(root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and "backups" not in path.parts
    }


def test_migrate_rolls_back_global_files_when_publication_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths, _, service = _prepared(tmp_path)
    before = _managed_files(paths.root)
    original_write = JsonDocumentStore.write

    def fail_registry_write(
        self: JsonDocumentStore, path: Path, document: JsonValue
    ) -> None:
        if path == paths.registry_file:
            raise OSError("injected registry publication failure")
        original_write(self, path, document)

    monkeypatch.setattr(JsonDocumentStore, "write", fail_registry_write)
    with pytest.raises(OSError):
        service.migrate("project", "https://example.test/new/project.git", None)

    after = _managed_files(paths.root)
    assert after == before
