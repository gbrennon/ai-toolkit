from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from ai_toolkit.agent_registry.errors import InvalidOperationError
from ai_toolkit.agent_registry.models import RepositoryStatus
from ai_toolkit.agent_registry.paths import RegistryPaths
from ai_toolkit.agent_registry.service import RegistryService


INSTANT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_initialize_creates_complete_empty_registry_tree_without_repository_changes(
    tmp_path: Path,
) -> None:
    registry_root = tmp_path / "registry"
    repository = tmp_path / "current-repository"
    repository.mkdir()
    marker = repository / "marker.txt"
    marker.write_text("unchanged", encoding="utf-8")
    before = marker.read_bytes()
    service = RegistryService(RegistryPaths(registry_root), clock=lambda: INSTANT)

    service.initialize()

    assert marker.read_bytes() == before
    assert {"skills", "hooks", "repos"} <= {
        path.name for path in registry_root.iterdir()
    }
    assert json.loads(
        (registry_root / "REGISTRY.json").read_text(encoding="utf-8")
    ) == {
        "schemaVersion": 1,
        "registryVersion": "1",
        "updatedAt": "2026-01-01T00:00:00Z",
        "repositories": [],
    }
    assert json.loads(
        (registry_root / "skills" / "manifest.json").read_text(encoding="utf-8")
    ) == {
        "schemaVersion": 1,
        "entries": [],
    }
    assert json.loads(
        (registry_root / "hooks" / "manifest.json").read_text(encoding="utf-8")
    ) == {
        "schemaVersion": 1,
        "entries": [],
    }
    assert (registry_root / "README.md").read_text(encoding="utf-8")
    assert (registry_root / "CHANGELOG.md").read_text(encoding="utf-8")


def test_initialize_is_idempotent_for_compatible_existing_tree(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    service = RegistryService(paths, clock=lambda: INSTANT)
    service.initialize()
    before = {
        path: path.read_bytes() for path in paths.root.rglob("*") if path.is_file()
    }

    service.initialize()

    assert before == {
        path: path.read_bytes() for path in paths.root.rglob("*") if path.is_file()
    }


def test_initialize_rejects_incompatible_existing_registry(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    paths.root.mkdir()
    paths.registry_file.write_text('{"schemaVersion": 99}', encoding="utf-8")
    service = RegistryService(paths, clock=lambda: INSTANT)

    with pytest.raises(InvalidOperationError):
        service.initialize()


def test_initial_registry_has_no_repository_records(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    RegistryService(paths, clock=lambda: INSTANT).initialize()

    payload = json.loads(paths.registry_file.read_text(encoding="utf-8"))
    assert payload["repositories"] == []
    assert RepositoryStatus.ACTIVE.value == "active"
