from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import pytest

import ai_toolkit.agent_registry.cli as cli
from ai_toolkit.agent_registry.errors import InvalidOperationError
from ai_toolkit.agent_registry.models import (
    AuditEvent,
    AuditReadReport,
    DiscoveryResult,
    RepositoryRecord,
    RepositoryStatus,
    ValidationIssue,
    ValidationReport,
)
from ai_toolkit.agent_registry.cli import RegistryServices

INSTANT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _record(tmp_path: Path) -> RepositoryRecord:
    return RepositoryRecord(
        "project",
        "https://example.test/acme/project",
        tmp_path,
        tmp_path / "AGENT.md",
        "a" * 64,
        RepositoryStatus.ACTIVE,
        INSTANT,
        INSTANT,
    )


class TestFakeService:
    def __init__(self, tmp_path: Path) -> None:
        self.record = _record(tmp_path)
        self.registration = self
        self.query = self
        self.migration = self
        self.archived = RepositoryRecord(
            "old-project",
            "https://example.test/acme/old-project",
            tmp_path / "old-project",
            tmp_path / "old-project" / "AGENT.md",
            "b" * 64,
            RepositoryStatus.ARCHIVED,
            INSTANT,
            INSTANT,
        )
        self.initialized = False
        self.registered: tuple[Path, bool] | None = None
        self.discovered: Path | str | None = None
        self.validated: str | None = None
        self.listed: bool | None = None
        self.migrated: tuple[str, str | None, Path | None] | None = None
        self.registration_error: InvalidOperationError | None = None
        self.discovery_result = DiscoveryResult(
            "project", self.record.agent_config_path, ValidationReport()
        )
        self.validation_report = ValidationReport()
        self.audit_report = AuditReadReport(
            events=(AuditEvent(INSTANT, "register", "project", "1", "success", 0.1),),
        )
        self.doctor_report = ValidationReport()

    def initialize(self) -> None:
        self.initialized = True

    def register(self, path: Path, review: bool = True) -> RepositoryRecord:
        if self.registration_error is not None:
            raise self.registration_error
        self.registered = (path, review)
        return self.record

    def audit(self, repository_id: str | None = None) -> AuditReadReport:
        self.audited = repository_id
        return self.audit_report

    def doctor(self) -> ValidationReport:
        return self.doctor_report
    def discover(self, path: Path | str) -> DiscoveryResult:
        self.discovered = path
        return self.discovery_result

    def validate(self, repository_id: str | None = None) -> ValidationReport:
        self.validated = repository_id
        return self.validation_report

    def list_repositories(
        self, include_inactive: bool = False
    ) -> tuple[RepositoryRecord, ...]:
        self.listed = include_inactive
        if include_inactive:
            return (self.archived, self.record)
        return (self.record,)


    def migrate(
        self,
        repository_id: str,
        git_remote: str | None = None,
        local_path: Path | None = None,
    ) -> RepositoryRecord:
        self.migrated = (repository_id, git_remote, local_path)
        return self.record


def _install_fake(monkeypatch: pytest.MonkeyPatch, fake: TestFakeService) -> None:
    def factory(_root: Path | None) -> RegistryServices:
        return cast(RegistryServices, fake)

    monkeypatch.setattr(cli, "_build_service", factory)


def test_help_lists_registry_commands(capsys: pytest.CaptureFixture[str]) -> None:
    result = cli.main(["--help"])
    output = capsys.readouterr()

    assert result == 0
    assert "initialize" in output.out
    assert "register" in output.out
    assert "audit" in output.out
    assert "doctor" in output.out
    assert "migrate" in output.out
    assert "discover" in output.out
    assert "validate" in output.out
    assert "list" in output.out


def test_initialize_dispatches_and_prints_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    _install_fake(monkeypatch, fake)

    result = cli.main(["initialize"])
    output = capsys.readouterr()

    assert result == 0
    assert fake.initialized
    assert "Initialized agent registry" in output.out
    assert output.err == ""


def test_register_no_review_dispatches_path_without_editor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    _install_fake(monkeypatch, fake)
    repository = tmp_path / "repository"

    result = cli.main(["register", str(repository), "--no-review"])
    output = capsys.readouterr()

    assert result == 0
    assert fake.registered == (repository, False)
    assert "Registered project" in output.out


def test_audit_dispatches_repository_and_prints_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    _install_fake(monkeypatch, fake)

    result = cli.main(["audit", "project"])
    output = capsys.readouterr()

    assert result == 0
    assert fake.audited == "project"
    assert "Audit events: 1" in output.out
    assert "project: register (success)" in output.out


def test_doctor_dispatches_and_reports_health(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    _install_fake(monkeypatch, fake)

    result = cli.main(["doctor"])
    output = capsys.readouterr()

    assert result == 0
    assert "Registry doctor: healthy" in output.out


def test_migrate_dispatches_remote_and_local_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    _install_fake(monkeypatch, fake)
    local_path = tmp_path / "moved"

    result = cli.main(
        [
            "migrate",
            "project",
            "--remote",
            "ssh://example.test/acme/project.git",
            "--local-path",
            str(local_path),
        ]
    )
    output = capsys.readouterr()

    assert result == 0
    assert fake.migrated == (
        "project",
        "ssh://example.test/acme/project.git",
        local_path,
    )
    assert "Migrated project" in output.out

def test_discover_dispatches_path_and_prints_global_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    _install_fake(monkeypatch, fake)
    repository = tmp_path / "repository"
    result = cli.main(["discover", str(repository)])
    output = capsys.readouterr()
    assert result == 0
    assert fake.discovered == repository
    assert "Discovered project" in output.out
    assert str(fake.record.agent_config_path) in output.out
def test_discover_returns_nonzero_for_validation_issues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    fake.discovery_result = DiscoveryResult(
        "project",
        fake.record.agent_config_path,
        ValidationReport((ValidationIssue("configSha256", "digest", "mismatch"),)),
    )
    _install_fake(monkeypatch, fake)
    result = cli.main(["discover", str(tmp_path / "repository")])
    output = capsys.readouterr()
    assert result == 1
    assert "Discovery found 1 issue(s)" in output.out
    assert "configSha256: mismatch" in output.out

def test_validate_dispatches_repository_and_reports_issues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    _install_fake(monkeypatch, fake)
    result = cli.main(["validate", "project"])
    output = capsys.readouterr()
    assert result == 0
    assert fake.validated == "project"
    assert "Registry validation: healthy" in output.out
    fake.validation_report = ValidationReport(
        (ValidationIssue("REGISTRY.json", "json", "malformed"),)
    )
    result = cli.main(["validate"])
    output = capsys.readouterr()
    assert result == 1
    assert fake.validated is None
    assert "Registry validation found 1 issue(s)" in output.out
    assert "REGISTRY.json: malformed" in output.out

def test_list_dispatches_include_inactive_and_prints_sorted_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    _install_fake(monkeypatch, fake)
    result = cli.main(["list", "--include-inactive"])
    output = capsys.readouterr()
    assert result == 0
    assert fake.listed is True
    assert "Repositories: 2" in output.out
    assert "old-project (archived)" in output.out
    assert "project (active)" in output.out

def test_invalid_command_returns_nonzero_and_writes_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = cli.main(["not-a-command"])
    output = capsys.readouterr()

    assert result != 0
    assert "invalid choice" in output.err


def test_service_error_returns_nonzero_on_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = TestFakeService(tmp_path)
    fake.registration_error = InvalidOperationError("registry is not initialized")
    _install_fake(monkeypatch, fake)

    result = cli.main(["register", str(tmp_path / "repository")])
    output = capsys.readouterr()

    assert result == 1
    assert "registry is not initialized" in output.err
    assert output.out == ""
