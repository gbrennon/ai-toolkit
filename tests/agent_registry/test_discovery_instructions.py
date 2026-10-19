from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from ai_toolkit.agent_registry.errors import InvalidOperationError, MissingOriginError
from ai_toolkit.agent_registry.git_port import GitPort
from ai_toolkit.agent_registry.json_document_store import JsonDocumentStore
from ai_toolkit.agent_registry.models import (
    DiscoveryResult,
    InstructionSourceKind,
    ValidationReport,
)
from ai_toolkit.agent_registry.paths import RegistryPaths
from ai_toolkit.agent_registry.service import RegistryService
from ai_toolkit.agent_registry.discovery import DiscoveryService
from ai_toolkit.agent_registry.instruction_resolver import InstructionResolver
from ai_toolkit.agent_registry.instruction_targets import GlobalInstructionTargets

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


def _registered(tmp_path: Path) -> tuple[RegistryPaths, Path, SimpleNamespace]:
    paths = RegistryPaths(tmp_path / "registry")
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "AGENT.md").write_text(
        _agent("project", "https://example.test/acme/project"), encoding="utf-8"
    )
    git = _git(repository, "https://example.test/acme/project.git")
    service = RegistryService(paths, git=cast(GitPort, git), clock=lambda: INSTANT)
    service.initialize()
    service.register(repository)
    return paths, repository, git


def _manifest_resolver(tmp_path: Path, global_path: Path) -> InstructionResolver:
    manifest = tmp_path / "agent_targets.txt"
    manifest.write_text(f"{global_path}\n", encoding="utf-8")
    return InstructionResolver(GlobalInstructionTargets(manifest))


def test_discovery_returns_local_then_managed_then_global_instructions(
    tmp_path: Path,
) -> None:
    paths, repository, git = _registered(tmp_path)
    global_path = tmp_path / "global" / "AGENTS.md"
    global_path.parent.mkdir()
    global_path.write_text("global instructions", encoding="utf-8")
    resolver = _manifest_resolver(tmp_path, global_path)
    registry_before = paths.registry_file.read_bytes()
    service = DiscoveryService(paths, git=cast(GitPort, git), resolver=resolver)

    local_result = service.discover(repository)

    assert local_result.instruction_resolution.selected is not None
    assert (
        local_result.instruction_resolution.selected.kind
        is InstructionSourceKind.LOCAL
    )
    assert paths.registry_file.read_bytes() == registry_before

    (repository / "AGENT.md").unlink()
    managed_result = service.discover(repository)

    assert managed_result.instruction_resolution.selected is not None
    assert (
        managed_result.instruction_resolution.selected.kind
        is InstructionSourceKind.PER_REPOSITORY
    )

    paths.repository("project").agent_config.unlink()
    global_result = service.discover(repository)

    assert global_result.instruction_resolution.selected is not None
    assert (
        global_result.instruction_resolution.selected.kind
        is InstructionSourceKind.GLOBAL
    )


def test_discover_reports_global_agent_digest_mismatch(tmp_path: Path) -> None:
    paths, repository, git = _registered(tmp_path)
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
    paths, repository, git = _registered(tmp_path)
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


def test_discover_reports_invalid_global_front_matter(tmp_path: Path) -> None:
    paths, repository, git = _registered(tmp_path)
    config = paths.repository("project").agent_config
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "repositoryId: project", "repositoryId: wrong"
        ),
        encoding="utf-8",
    )

    result = DiscoveryService(paths, git=cast(GitPort, git)).discover(repository)

    assert any(issue.code == "mismatch" for issue in result.validation_report.issues)


def test_resolve_instructions_uses_local_file_for_unregistered_repository(
    tmp_path: Path,
) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "AGENT.md").write_text("local only", encoding="utf-8")
    git = _git(repository, "https://example.test/acme/project.git")
    RegistryService(paths, git=cast(GitPort, git), clock=lambda: INSTANT).initialize()
    service = DiscoveryService(paths, git=cast(GitPort, git))

    resolution = service.resolve_instructions(repository)

    assert resolution.selected is not None
    assert resolution.selected.kind is InstructionSourceKind.LOCAL
    with pytest.raises(InvalidOperationError, match="no active registry mapping"):
        service.discover(repository)


def test_resolve_instructions_falls_back_to_global_for_unregistered_repository(
    tmp_path: Path,
) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    repository = tmp_path / "repository"
    repository.mkdir()
    git = _git(repository, "https://example.test/acme/project.git")
    RegistryService(paths, git=cast(GitPort, git), clock=lambda: INSTANT).initialize()
    global_path = tmp_path / "global" / "AGENTS.md"
    global_path.parent.mkdir()
    global_path.write_text("global only", encoding="utf-8")
    service = DiscoveryService(
        paths, git=cast(GitPort, git), resolver=_manifest_resolver(tmp_path, global_path)
    )

    resolution = service.resolve_instructions(repository)

    assert resolution.selected is not None
    assert resolution.selected.kind is InstructionSourceKind.GLOBAL
    assert resolution.selected.path == global_path.resolve()


def test_resolve_instructions_handles_repository_without_origin(
    tmp_path: Path,
) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "AGENT.md").write_text("local only", encoding="utf-8")
    git = _git(repository, "https://example.test/acme/project.git")
    git.origin = False
    RegistryService(paths, git=cast(GitPort, git), clock=lambda: INSTANT).initialize()
    service = DiscoveryService(paths, git=cast(GitPort, git))

    resolution = service.resolve_instructions(repository)

    assert resolution.selected is not None
    assert resolution.selected.kind is InstructionSourceKind.LOCAL


def test_discovery_result_is_frozen_and_requires_absolute_path(tmp_path: Path) -> None:
    result = DiscoveryResult(
        "project", (tmp_path / "AGENT.md").resolve(), ValidationReport()
    )

    with pytest.raises(FrozenInstanceError):
        setattr(result, "repository_id", "changed")
    with pytest.raises(ValueError, match="absolute"):
        DiscoveryResult("project", Path("AGENT.md"), ValidationReport())
