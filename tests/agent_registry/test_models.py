from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_toolkit.agent_registry.models import (
    RegistryDocument,
    RepositoryRecord,
    RepositoryStatus,
)


def _record() -> RepositoryRecord:
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return RepositoryRecord(
        repository_id="owner-repo",
        git_remote="https://example.test/owner/repo",
        local_path=Path("/work/repo"),
        agent_config_path=Path("/registry/repos/owner-repo/AGENT.md"),
        config_sha256="a" * 64,
        status=RepositoryStatus.ACTIVE,
        registered_at=instant,
        updated_at=instant,
    )


def test_repository_record_serializes_external_field_names_and_utc() -> None:
    record = _record()

    serialized = record.to_json()

    assert serialized["id"] == "owner-repo"
    assert serialized["registeredAt"] == "2026-01-01T00:00:00Z"
    assert serialized["status"] == "active"


def test_registry_document_serializes_nested_records() -> None:
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    document = RegistryDocument(1, "1", instant, (_record(),))

    serialized = document.to_json()

    assert serialized["schemaVersion"] == 1
    assert serialized["repositories"] == [_record().to_json()]


def test_repository_record_is_immutable() -> None:
    record = _record()

    with pytest.raises(FrozenInstanceError):
        setattr(record, "repository_id", "changed")
