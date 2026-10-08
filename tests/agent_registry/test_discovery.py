from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from ai_toolkit.agent_registry.errors import (
    InvalidOperationError,
    MissingOriginError,
    SchemaValidationError,
)
from ai_toolkit.agent_registry.git_port import GitPort
from ai_toolkit.agent_registry.json_document_store import JsonDocumentStore
from ai_toolkit.agent_registry.models import (
    DiscoveryResult,
    RepositoryStatus,
    ValidationReport,
)
from ai_toolkit.agent_registry.paths import RegistryPaths
from ai_toolkit.agent_registry.service import RegistryService
from ai_toolkit.agent_registry.discovery import DiscoveryService

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


def _git(root: Path, remote: str) -> SimpleNamespace:
    state = SimpleNamespace(root=root.resolve(), remote=remote, origin=True)

    def resolve_worktree_root(_path: Path) -> Path:
        return state.root

    def canonical_remote(_path: Path) -> str:
        if not state.origin:
            raise MissingOriginError(state.root)
        return "origin"

    def remote_url(_path: Path, _remote: str = "origin") -> str:
        if not state.origin:
            raise MissingOriginError(state.root)
        return state.remote

    state.resolve_worktree_root = resolve_worktree_root
    state.canonical_remote = canonical_remote
    state.remote_url = remote_url
    return state


def _prepared(
    tmp_path: Path,
    remote: str = "https://example.test/acme/project.git",
) -> tuple[RegistryPaths, Path, SimpleNamespace, RegistryService]:
    paths = RegistryPaths(tmp_path / "registry")
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "AGENT.md").write_text(
        _agent("project", "https://example.test/acme/project"), encoding="utf-8"
    )
    git = _git(repository, remote)
    service = RegistryService(paths, git=cast(GitPort, git), clock=lambda: INSTANT)
    service.initialize()
    service.register(repository)
    return paths, repository, git, service


def test_discover_returns_valid_global_configuration_without_reading_repository_agent(
    tmp_path: Path,
) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    local_agent = repository / "AGENT.md"
    local_agent.unlink()

    result = DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)

    assert result.repository_id == "project"
    assert result.agent_config_path == paths.repository("project").agent_config
    assert result.agent_config_path.is_absolute()
    assert result.validation_report.is_valid
    assert not local_agent.exists()


def test_discover_uses_owner_qualified_id_after_repository_name_collision(
    tmp_path: Path,
) -> None:
    paths, repository, git, service = _prepared(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    git.root = other.resolve()
    git.remote = "https://example.test/other/project.git"
    (other / "AGENT.md").write_text(
        _agent("other-project", "https://example.test/other/project"), encoding="utf-8"
    )
    service.register(other)

    result = DiscoveryService(paths, git=cast(GitPort, git)).discover(other)

    assert result.repository_id == "other-project"
    assert result.validation_report.is_valid


def test_discover_uses_exact_active_local_root_when_origin_is_missing(
    tmp_path: Path,
) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    git.origin = False

    result = DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)

    assert result.repository_id == "project"
    assert result.validation_report.is_valid


def test_discover_rejects_missing_mapping_without_local_path_fallback(
    tmp_path: Path,
) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    git.root = (tmp_path / "unregistered").resolve()
    git.remote = "https://example.test/acme/unregistered.git"

    with pytest.raises(InvalidOperationError, match="no active registry mapping"):
        DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)


def test_discover_rejects_inactive_mapping(tmp_path: Path) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    payload = json.loads(paths.registry_file.read_text(encoding="utf-8"))
    payload["repositories"][0]["status"] = RepositoryStatus.ARCHIVED.value
    JsonDocumentStore().write(paths.registry_file, payload)

    with pytest.raises(InvalidOperationError, match="inactive"):
        DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)


def test_discover_rejects_remote_path_disagreement(tmp_path: Path) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    payload = json.loads(paths.registry_file.read_text(encoding="utf-8"))
    payload["repositories"][0]["localPath"] = str((tmp_path / "other-root").resolve())
    JsonDocumentStore().write(paths.registry_file, payload)

    with pytest.raises(InvalidOperationError, match="local path"):
        DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)


def test_discover_reports_global_agent_digest_mismatch(tmp_path: Path) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    config = paths.repository("project").agent_config
    config.write_text(
        config.read_text(encoding="utf-8") + "changed\n", encoding="utf-8"
    )

    result = DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)

    assert not result.validation_report.is_valid
    assert any(issue.code == "digest" for issue in result.validation_report.issues)


def test_discover_reports_metadata_and_dependency_manifest_errors(
    tmp_path: Path,
) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    repo_paths = paths.repository("project")
    JsonDocumentStore().write(repo_paths.metadata, {"unexpected": True})
    JsonDocumentStore().write(
        repo_paths.skills,
        {"schemaVersion": 1, "entries": [{"id": "../escape", "version": "1"}]},
    )

    result = DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)

    assert not result.validation_report.is_valid
    codes = {issue.code for issue in result.validation_report.issues}
    assert "metadata" in codes
    assert "dependencies" in codes


def test_discover_rejects_duplicate_active_local_root_mapping(tmp_path: Path) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    payload = json.loads(paths.registry_file.read_text(encoding="utf-8"))
    duplicate = dict(payload["repositories"][0])
    duplicate["id"] = "other"
    duplicate["gitRemote"] = "https://example.test/other/other"
    duplicate["agentConfigPath"] = str(paths.repository("other").agent_config)
    payload["repositories"].append(duplicate)
    JsonDocumentStore().write(paths.registry_file, payload)

    with pytest.raises(SchemaValidationError, match="duplicate active path"):
        DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)


def test_discover_uses_normalized_origin_equivalence(tmp_path: Path) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    git.remote = "ssh://EXAMPLE.TEST/acme/project.git"

    result = DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)

    assert result.repository_id == "project"
    assert result.validation_report.is_valid


def test_discover_reports_invalid_global_front_matter(tmp_path: Path) -> None:
    paths, repository, git, _ = _prepared(tmp_path)
    config = paths.repository("project").agent_config
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "repositoryId: project", "repositoryId: wrong"
        ),
        encoding="utf-8",
    )

    result = DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)

    assert any(issue.code == "mismatch" for issue in result.validation_report.issues)


def test_discover_requires_initialized_registry(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    repository = tmp_path / "repository"
    repository.mkdir()
    git = _git(repository, "https://example.test/acme/project.git")

    with pytest.raises(InvalidOperationError, match="not initialized"):
        DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)


def test_discovery_result_is_frozen_and_requires_absolute_path(tmp_path: Path) -> None:
    result = DiscoveryResult(
        "project", (tmp_path / "AGENT.md").resolve(), ValidationReport()
    )

    with pytest.raises(FrozenInstanceError):
        setattr(result, "repository_id", "changed")
    with pytest.raises(ValueError, match="absolute"):
        DiscoveryResult("project", Path("AGENT.md"), ValidationReport())
