from collections.abc import Callable
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import cast

import pytest

from ai_toolkit.agent_registry.audit import AuditEventStore
from ai_toolkit.agent_registry.errors import InvalidOperationError
from ai_toolkit.agent_registry.models import AuditEvent, ValidationReport
from ai_toolkit.agent_registry.models._json import JsonValue
from ai_toolkit.agent_registry.paths import RegistryPaths
from ai_toolkit.agent_registry.service import RegistryService


INSTANT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _record(paths: RegistryPaths, repository_id: str, status: str = "active") -> dict[str, JsonValue]:
    return {
        "id": repository_id,
        "gitRemote": f"https://example.test/acme/{repository_id}.git",
        "localPath": str((paths.root.parent / f"local-{repository_id}").resolve()),
        "agentConfigPath": str(paths.repository(repository_id).agent_config),
        "configSha256": "0" * 64,
        "status": status,
        "registeredAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }


def _set_records(paths: RegistryPaths, records: list[dict[str, JsonValue]]) -> None:
    document = json.loads(paths.registry_file.read_text(encoding="utf-8"))
    document["repositories"] = records
    paths.registry_file.write_text(json.dumps(document), encoding="utf-8")


def _event(repository_id: str, sequence: int) -> AuditEvent:
    return AuditEvent(
        INSTANT,
        "register",
        repository_id,
        "1",
        "success",
        float(sequence),
        {"sequence": sequence},
    )


def _service(tmp_path: Path) -> tuple[RegistryPaths, RegistryService]:
    paths = RegistryPaths(tmp_path / "registry")
    service = RegistryService(paths, clock=lambda: INSTANT)
    service.initialize()
    return paths, service


def test_audit_orders_active_repositories_and_filters_one_repository(tmp_path: Path) -> None:
    paths, service = _service(tmp_path)
    _set_records(
        paths,
        [_record(paths, "beta"), _record(paths, "alpha"), _record(paths, "blocked", "blocked")],
    )
    AuditEventStore(paths.repository("alpha").changes_audit).append(_event("alpha", 1))
    AuditEventStore(paths.repository("alpha").changes_audit).append(_event("alpha", 3))
    AuditEventStore(paths.repository("beta").changes_audit).append(_event("beta", 2))
    AuditEventStore(paths.repository("beta").changes_audit).append(_event("alpha", 9))

    report = service.audit()
    selected = service.audit("beta")

    assert [event.repository_id for event in report.events] == ["alpha", "alpha", "beta", "alpha"]
    assert [event.metadata["sequence"] for event in report.events] == [1, 3, 2, 9]
    assert [event.metadata["sequence"] for event in selected.events] == [2]


def test_audit_preserves_malformed_line_issues_and_valid_event_order(tmp_path: Path) -> None:
    paths, service = _service(tmp_path)
    _set_records(paths, [_record(paths, "alpha")])
    audit_path = paths.repository("alpha").changes_audit
    audit = AuditEventStore(audit_path)
    audit.append(_event("alpha", 1))
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write("{bad}\n")
    audit.append(_event("alpha", 2))

    report = service.audit("alpha")

    assert [event.metadata["sequence"] for event in report.events] == [1, 2]
    assert len(report.issues) == 1
    assert "line 2" in report.issues[0].field


def test_audit_rejects_unknown_repository_id(tmp_path: Path) -> None:
    paths, service = _service(tmp_path)
    _set_records(paths, [_record(paths, "alpha")])

    with pytest.raises(InvalidOperationError, match="unknown repository id"):
        service.audit("missing")


def test_audit_rejects_uninitialized_registry(tmp_path: Path) -> None:
    service = RegistryService(RegistryPaths(tmp_path / "registry"), clock=lambda: INSTANT)

    with pytest.raises(InvalidOperationError, match="not initialized"):
        service.audit()


def test_doctor_reports_valid_initialized_registry(tmp_path: Path) -> None:
    _, service = _service(tmp_path)

    report = service.doctor()

    assert report == ValidationReport()


def test_doctor_reports_missing_managed_root_entries(tmp_path: Path) -> None:
    paths, service = _service(tmp_path)
    paths.registry_file.unlink()
    paths.readme.unlink()
    paths.changelog.unlink()
    (paths.skills_dir / "manifest.json").unlink()
    (paths.hooks_dir / "manifest.json").unlink()
    shutil.rmtree(paths.repos_dir)

    report = service.doctor()

    fields = {issue.field for issue in report.issues}
    assert fields == {
        str(paths.registry_file),
        str(paths.readme),
        str(paths.changelog),
        str(paths.skills_dir / "manifest.json"),
        str(paths.hooks_dir / "manifest.json"),
        str(paths.repos_dir),
    }


def test_doctor_reports_corrupt_root_and_invalid_records(tmp_path: Path) -> None:
    paths, service = _service(tmp_path)
    paths.registry_file.write_text("{bad", encoding="utf-8")

    corrupt = service.doctor()

    assert any(issue.field == str(paths.registry_file) for issue in corrupt.issues)
    paths.registry_file.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "registryVersion": "1",
                "updatedAt": "2026-01-01T00:00:00Z",
                "repositories": [_record(paths, "alpha") | {"status": "invalid"}],
            }
        ),
        encoding="utf-8",
    )

    invalid = service.doctor()

    assert any(issue.field == "repositories[0].status" for issue in invalid.issues)


def test_doctor_does_not_mutate_registry_or_read_local_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths, service = _service(tmp_path)
    local_file = (tmp_path / "repository" / "AGENT.md").resolve()
    local_file.parent.mkdir()
    local_file.write_text("repository-only", encoding="utf-8")
    _set_records(paths, [_record(paths, "alpha") | {"localPath": str(local_file.parent)}])
    before = {path: path.read_bytes() for path in paths.root.rglob("*") if path.is_file()}
    original_read_text = cast(Callable[..., str], Path.read_text)

    def reject_local(path: Path, *args: object, **kwargs: object) -> str:
        if path == local_file:
            raise AssertionError("doctor read a repository-local file")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", reject_local)

    report = service.doctor()

    after = {path: path.read_bytes() for path in paths.root.rglob("*") if path.is_file()}
    assert report.is_valid
    assert after == before
