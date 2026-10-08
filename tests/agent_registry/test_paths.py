from pathlib import Path

import pytest

from ai_toolkit.agent_registry.errors import PathEscapeError
from ai_toolkit.agent_registry.path_containment import PathContainment
from ai_toolkit.agent_registry.paths import RegistryPaths


def test_registry_paths_derive_global_and_repository_paths(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    repository = paths.repository("owner-repo")

    assert paths.root == (tmp_path / "registry").resolve()
    assert paths.registry_file == paths.root / "REGISTRY.json"
    assert paths.readme == paths.root / "README.md"
    assert paths.changelog == paths.root / "CHANGELOG.md"
    assert paths.skills_dir == paths.root / "skills"
    assert paths.hooks_dir == paths.root / "hooks"
    assert paths.repos_dir == paths.root / "repos"
    assert repository.directory == paths.repos_dir / "owner-repo"
    assert repository.agent_config == repository.directory / "AGENT.md"
    assert repository.metadata == repository.directory / "metadata.json"
    assert repository.skills == repository.directory / "skills.json"
    assert repository.hooks == repository.directory / "hooks.json"
    assert repository.audit_dir == repository.directory / "audit"
    assert repository.changes_audit == repository.audit_dir / "changes.ndjson"


def test_registry_paths_reject_unsafe_repository_ids(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")

    with pytest.raises(PathEscapeError):
        paths.repository("../outside")
    with pytest.raises(PathEscapeError):
        paths.repository("owner/repository")
    with pytest.raises(PathEscapeError):
        paths.repository("Repo")


def test_path_containment_rejects_traversal_and_absolute_references(tmp_path: Path) -> None:
    containment = PathContainment(tmp_path / "root")

    with pytest.raises(PathEscapeError):
        containment.resolve("nested/../outside")
    with pytest.raises(PathEscapeError):
        containment.resolve(Path("/tmp/outside"))


def test_path_containment_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    containment = PathContainment(root)

    with pytest.raises(PathEscapeError):
        containment.resolve("link/file")


def test_path_containment_resolves_safe_reference(tmp_path: Path) -> None:
    root = tmp_path / "root"
    containment = PathContainment(root)

    assert containment.resolve("nested/file") == root.resolve() / "nested/file"
