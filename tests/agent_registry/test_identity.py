from pathlib import Path

import pytest

from ai_toolkit.agent_registry.errors import IdentityCollisionError, RemoteNormalizationError
from ai_toolkit.agent_registry.identity import (
    choose_repository_id,
    normalize_remote,
    normalize_repository_id,
    validate_unique_local_paths,
    validate_unique_remotes,
)


def test_supported_remote_url_forms_have_one_credential_free_identity() -> None:
    identities = {
        normalize_remote("https://GitHub.com/Acme/Project.git/"),
        normalize_remote("ssh://git:secret@github.com/Acme/Project.git"),
        normalize_remote("git@GitHub.com:Acme/Project.git"),
    }

    assert len(identities) == 1
    identity = identities.pop()
    assert identity.host == "github.com"
    assert identity.owner == "acme"
    assert identity.repository == "project"
    assert identity.normalized == "github.com/acme/project"
    assert "@" not in identity.normalized


@pytest.mark.parametrize(
    "remote",
    [
        "",
        "https://",
        "http://github.com/owner/repository.git",
        "ssh://github.com",
        "git@github.com:repository.git",
        "https://github.com/owner/repository?token=secret",
        "https://github.com/owner/../repository.git",
        "https://github.com//repository.git",
    ],
)
def test_malformed_or_unusable_remote_urls_are_rejected(remote: str) -> None:
    with pytest.raises(RemoteNormalizationError):
        normalize_remote(remote)


def test_repository_ids_are_lowercase_and_safe_for_registry_paths() -> None:
    assert normalize_repository_id("Acme / Nested Repository") == "acme-nested-repository"
    assert normalize_repository_id("--Mixed.Case_42--") == "mixed.case_42"


def test_same_remote_reuses_unqualified_repository_id() -> None:
    remote = normalize_remote("https://example.test/acme/project.git")

    selected = choose_repository_id(remote, {"project": remote})

    assert selected == "project"


def test_different_remote_uses_owner_qualified_repository_id() -> None:
    existing = normalize_remote("https://example.test/other/project.git")
    remote = normalize_remote("https://example.test/acme/project.git")

    selected = choose_repository_id(remote, {"project": existing})

    assert selected == "acme-project"


def test_nested_owner_groups_are_joined_deterministically() -> None:
    existing = normalize_remote("https://example.test/other/project.git")
    remote = normalize_remote("https://example.test/acme/platform/project.git")

    selected = choose_repository_id(remote, {"project": existing})

    assert selected == "acme-platform-project"


def test_occupied_qualified_repository_id_fails_explicitly() -> None:
    first = normalize_remote("https://example.test/other/project.git")
    second = normalize_remote("https://example.test/acme/project.git")
    qualified = normalize_remote("https://example.test/different/project.git")

    with pytest.raises(IdentityCollisionError, match="acme-project"):
        choose_repository_id(second, {"project": first, "acme-project": qualified})

def test_owner_qualification_accepts_record_mappings() -> None:
    existing = [
        {
            "id": "project",
            "gitRemote": "https://example.test/other/project.git",
        }
    ]
    remote = normalize_remote("https://example.test/acme/project.git")

    selected = choose_repository_id(remote, existing)

    assert selected == "acme-project"


def test_normalized_remote_uniqueness_rejects_duplicate_identity() -> None:
    records = [
        {"id": "one", "gitRemote": "https://example.test/acme/project.git"},
        {"id": "two", "gitRemote": "ssh://git@example.test/acme/project.git"},
    ]

    with pytest.raises(IdentityCollisionError, match="normalized remote"):
        validate_unique_remotes(records)


def test_active_local_path_uniqueness_ignores_archived_records(tmp_path: Path) -> None:
    local_path = (tmp_path / "repository").resolve()
    records = [
        {"id": "archived", "localPath": str(local_path), "status": "archived"},
        {"id": "active", "localPath": str(local_path), "status": "active"},
    ]

    validate_unique_local_paths(records)


def test_active_local_path_uniqueness_rejects_duplicate_active_paths(
    tmp_path: Path,
) -> None:
    local_path = (tmp_path / "repository").resolve()
    records = [
        {"id": "one", "localPath": str(local_path), "status": "active"},
        {"id": "two", "localPath": str(local_path / "nested" / ".."), "status": "active"},
    ]

    with pytest.raises(IdentityCollisionError, match="local path"):
        validate_unique_local_paths(records)
