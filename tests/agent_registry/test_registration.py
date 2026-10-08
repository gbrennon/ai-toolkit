from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from ai_toolkit.agent_registry.dependencies import (
    parse_hook_manifest,
    parse_skill_manifest,
)
from ai_toolkit.agent_registry.editor_port import EditorPort
from ai_toolkit.agent_registry.errors import (
    AtomicWriteError,
    EditorExecutionError,
    IdentityCollisionError,
    InvalidOperationError,
)
from ai_toolkit.agent_registry.git_port import GitPort
from ai_toolkit.agent_registry.json_document_store import JsonDocumentStore
from ai_toolkit.agent_registry.markdown import validate_agent_markdown
from ai_toolkit.agent_registry.models import RepositoryStatus
from ai_toolkit.agent_registry.models._json import JsonValue
from ai_toolkit.agent_registry.paths import RegistryPaths
from ai_toolkit.agent_registry.service import RegistryService

INSTANT = datetime(2026, 1, 1, tzinfo=timezone.utc)


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


def _editor(failure: Exception | None = None) -> tuple[EditorPort, list[str]]:
    inputs: list[str] = []

    def edit(content: str) -> str:
        inputs.append(content)
        if failure is not None:
            raise failure
        return content

    return cast(EditorPort, SimpleNamespace(edit=edit)), inputs


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
            "Identity.",
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


def _prepared(
    tmp_path: Path, remote: str = "https://example.test/acme/project.git"
) -> tuple[RegistryPaths, Path, SimpleNamespace, list[str], RegistryService]:
    paths = RegistryPaths(tmp_path / "registry")
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "AGENT.md").write_text(
        _agent("project", "https://example.test/acme/project"), encoding="utf-8"
    )
    git = _git(repository, remote)
    editor, inputs = _editor()
    service = RegistryService(
        paths, git=cast(GitPort, git), editor=editor, clock=lambda: INSTANT
    )
    service.initialize()
    return paths, repository, git, inputs, service


def test_register_publishes_root_agent_and_complete_repository_artifacts(
    tmp_path: Path,
) -> None:
    paths, repository, _, inputs, service = _prepared(tmp_path)
    before = (repository / "AGENT.md").read_bytes()

    record = service.register(repository)

    repository_paths = paths.repository(record.repository_id)
    assert record.repository_id == "project"
    assert record.status is RepositoryStatus.ACTIVE
    assert repository_paths.agent_config.read_bytes() == before
    assert repository_paths.metadata.is_file()
    assert repository_paths.changes_audit.is_file()
    assert parse_skill_manifest(json.loads(repository_paths.skills.read_text())) == ()
    assert parse_hook_manifest(json.loads(repository_paths.hooks.read_text())) == ()
    assert validate_agent_markdown(
        repository_paths.agent_config.read_text(), record
    ).is_valid
    assert (repository / "AGENT.md").read_bytes() == before
    assert inputs == [before.decode("utf-8")]


def test_register_can_skip_editor_when_review_is_not_requested(tmp_path: Path) -> None:
    paths, repository, git, _, _ = _prepared(tmp_path)
    failing_editor, inputs = _editor(EditorExecutionError("editor failed"))
    service = RegistryService(
        paths,
        git=cast(GitPort, git),
        editor=failing_editor,
        clock=lambda: INSTANT,
    )

    record = service.register(repository, review=False)

    assert paths.repository(record.repository_id).agent_config.is_file()
    assert inputs == []


def test_register_editor_failure_leaves_registry_and_repository_tree_unchanged(
    tmp_path: Path,
) -> None:
    paths, repository, git, _, service = _prepared(tmp_path)
    registry_before = paths.registry_file.read_bytes()
    failing_editor, _ = _editor(EditorExecutionError("editor failed"))
    failing = RegistryService(
        paths,
        git=cast(GitPort, git),
        editor=failing_editor,
        clock=lambda: INSTANT,
    )

    with pytest.raises(EditorExecutionError):
        failing.register(repository)

    assert paths.registry_file.read_bytes() == registry_before
    assert not (paths.repos_dir / "project").exists()
    assert (repository / "AGENT.md").read_bytes() == _agent(
        "project", "https://example.test/acme/project"
    ).encode("utf-8")
    assert service is not None


def test_register_same_identity_is_idempotent(tmp_path: Path) -> None:
    paths, repository, git, _, service = _prepared(tmp_path)
    first = service.register(repository)
    before = {
        path: path.read_bytes()
        for path in paths.repository(first.repository_id).directory.rglob("*")
        if path.is_file()
    }

    second = service.register(repository)

    after = {
        path: path.read_bytes()
        for path in paths.repository(first.repository_id).directory.rglob("*")
        if path.is_file()
    }
    assert second == first
    assert before == after


def test_register_rejects_normalized_remote_collision(tmp_path: Path) -> None:
    paths, repository, git, _, service = _prepared(tmp_path)
    service.register(repository)
    other = tmp_path / "other"
    other.mkdir()
    git.root = other.resolve()
    git.remote = "ssh://EXAMPLE.TEST/acme/project.git"
    (other / "AGENT.md").write_text(
        _agent("project", "https://example.test/acme/project"), encoding="utf-8"
    )

    with pytest.raises(IdentityCollisionError):
        service.register(other)


def test_register_qualifies_owner_on_repository_name_collision(tmp_path: Path) -> None:
    paths, repository, git, _, service = _prepared(tmp_path)
    service.register(repository)
    other = tmp_path / "other"
    other.mkdir()
    git.root = other.resolve()
    git.remote = "https://example.test/other/project.git"
    (other / "AGENT.md").write_text(
        _agent("other-project", "https://example.test/other/project"), encoding="utf-8"
    )

    record = service.register(other)

    assert record.repository_id == "other-project"


def test_register_rejects_active_local_path_collision(tmp_path: Path) -> None:
    paths, repository, git, _, service = _prepared(tmp_path)
    service.register(repository)
    git.remote = "https://example.test/other/project.git"

    with pytest.raises(IdentityCollisionError):
        service.register(repository)


def test_register_requires_root_agent_file(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    repository = tmp_path / "repository"
    repository.mkdir()
    git = _git(repository, "https://example.test/acme/project.git")
    editor, _ = _editor()
    service = RegistryService(
        paths, git=cast(GitPort, git), editor=editor, clock=lambda: INSTANT
    )
    service.initialize()

    with pytest.raises(InvalidOperationError):
        service.register(repository)


def test_register_index_failure_removes_published_repository_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths, repository, git, _, _ = _prepared(tmp_path)
    registry_before = paths.registry_file.read_bytes()

    def fail_write(_self: JsonDocumentStore, path: Path, document: JsonValue) -> None:
        raise AtomicWriteError(f"cannot write {path}")

    monkeypatch.setattr(JsonDocumentStore, "write", fail_write)
    editor, _ = _editor()
    failing = RegistryService(
        paths,
        git=cast(GitPort, git),
        editor=editor,
        clock=lambda: INSTANT,
    )

    with pytest.raises(AtomicWriteError):
        failing.register(repository)

    assert paths.registry_file.read_bytes() == registry_before
    assert not (paths.repos_dir / "project").exists()
