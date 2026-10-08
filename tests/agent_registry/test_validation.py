from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
import pytest

from ai_toolkit.agent_registry.models import (
    RegistryDocument,
    RepositoryRecord,
    RepositoryStatus,
)
from ai_toolkit.agent_registry.markdown import (
    parse_agent_document,
    render_agent_markdown,
    validate_agent_markdown,
)
from ai_toolkit.agent_registry.paths import RegistryPaths
from ai_toolkit.agent_registry.validation import (
    parse_registry_document,
    validate_registry_document,
)


def _record(tmp_path: Path, name: str = "project") -> dict[str, object]:
    root = (tmp_path / "repo").resolve()
    return {
        "id": name,
        "gitRemote": "https://example.test/acme/project.git",
        "localPath": str(root),
        "agentConfigPath": str(tmp_path / "registry" / "repos" / name / "AGENT.md"),
        "configSha256": "a" * 64,
        "status": "active",
        "registeredAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-02T00:00:00Z",
    }


def _document(tmp_path: Path, records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "registryVersion": "1",
        "updatedAt": "2026-01-03T00:00:00Z",
        "repositories": records,
    }


def test_valid_registry_document_parses_into_immutable_models(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    document = parse_registry_document(_document(tmp_path, [_record(tmp_path)]), paths)

    assert isinstance(document, RegistryDocument)
    assert document.repositories[0].status is RepositoryStatus.ACTIVE
    assert document.repositories[0].local_path.is_absolute()
    assert document.to_json()["schemaVersion"] == 1
    with pytest.raises(AttributeError):
        cast(Any, document).registry_version = "changed"


def test_validation_reports_independent_root_and_record_issues(tmp_path: Path) -> None:
    record = _record(tmp_path)
    record.update(
        {
            "unknown": True,
            "gitRemote": " https://example.test/acme/project.git",
            "localPath": "relative/repo",
            "agentConfigPath": str(tmp_path / "outside" / "AGENT.md"),
            "configSha256": "A" * 63,
            "status": "invalid",
            "registeredAt": "2026-01-01T00:00:00+00:00",
        }
    )
    payload = _document(tmp_path, [record])
    payload["unknownRoot"] = True
    payload["updatedAt"] = "2026-01-03T00:00:00+00:00"

    report = validate_registry_document(payload, RegistryPaths(tmp_path / "registry"))

    fields = {issue.field.rsplit(".", 1)[-1] for issue in report.issues}
    assert {"unknownRoot", "unknown", "gitRemote", "localPath", "agentConfigPath", "configSha256", "status", "registeredAt", "updatedAt"} <= fields
    assert not report.is_valid


def test_validation_rejects_duplicate_ids_remotes_and_active_paths(tmp_path: Path) -> None:
    first = _record(tmp_path, "first")
    second = _record(tmp_path, "first")
    second["gitRemote"] = "https://example.test/acme/other.git"
    second["agentConfigPath"] = str(tmp_path / "registry" / "repos" / "second" / "AGENT.md")
    third = _record(tmp_path, "third")
    third["gitRemote"] = "https://example.test/acme/project.git"
    third["agentConfigPath"] = str(tmp_path / "registry" / "repos" / "third" / "AGENT.md")

    report = validate_registry_document(
        _document(tmp_path, [first, second, third]), RegistryPaths(tmp_path / "registry")
    )
    codes = {issue.code for issue in report.issues}
    assert {"duplicate-id", "duplicate-remote", "duplicate-local-path"} <= codes


def test_validation_rejects_missing_record_fields(tmp_path: Path) -> None:
    record = _record(tmp_path)
    record.pop("status")

    report = validate_registry_document(_document(tmp_path, [record]), RegistryPaths(tmp_path / "registry"))

    assert any(issue.field.endswith(".status") for issue in report.issues)


def test_agent_validation_reports_duplicate_and_missing_headings(tmp_path: Path) -> None:
    registry, record = _models(tmp_path)
    rendered = render_agent_markdown(record, registry).replace("## Hooks", "## Scope")

    report = validate_agent_markdown(rendered, record)

    assert {issue.code for issue in report.issues} == {"duplicate-heading", "missing-heading"}



def test_registry_models_serialize_utc_z_timestamps() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    record = RepositoryRecord(
        repository_id="project",
        git_remote="https://example.test/acme/project",
        local_path=Path("/tmp/project"),
        agent_config_path=Path("/tmp/registry/repos/project/AGENT.md"),
        config_sha256="a" * 64,
        status=RepositoryStatus.ACTIVE,
        registered_at=timestamp,
        updated_at=timestamp,
    )

    assert record.to_json()["registeredAt"] == "2026-01-01T00:00:00Z"



def _models(tmp_path: Path) -> tuple[RegistryDocument, RepositoryRecord]:
    instant = datetime(2026, 1, 3, tzinfo=timezone.utc)
    record = RepositoryRecord(
        repository_id="project",
        git_remote="https://example.test/acme/project.git",
        local_path=(tmp_path / "repo").resolve(),
        agent_config_path=(tmp_path / "registry" / "repos" / "project" / "AGENT.md").resolve(),
        config_sha256="a" * 64,
        status=RepositoryStatus.ACTIVE,
        registered_at=instant,
        updated_at=instant,
    )
    return RegistryDocument(1, "1", instant, (record,)), record


def test_agent_renderer_is_deterministic_and_parser_validates_contract(tmp_path: Path) -> None:
    registry, record = _models(tmp_path)

    rendered = render_agent_markdown(record, registry)

    assert rendered == render_agent_markdown(record, registry)
    front_matter, headings = parse_agent_document(rendered)
    assert front_matter.repository_id == record.repository_id
    assert headings.count("Scope") == 1
    assert validate_agent_markdown(rendered, record).is_valid


def test_agent_validation_rejects_mismatch_duplicate_and_wrong_headings(tmp_path: Path) -> None:
    registry, record = _models(tmp_path)
    rendered = render_agent_markdown(record, registry)
    malformed = rendered.replace("repositoryId: project", "repositoryId: other")
    malformed = malformed.replace("## Scope", "### Scope").replace("## Hooks", "## Scope")

    report = validate_agent_markdown(malformed, record)

    assert not report.is_valid
    assert {issue.code for issue in report.issues} == {"markdown"}
