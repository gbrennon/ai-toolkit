from pathlib import Path

from .audit import AuditEventStore
from .errors import InvalidOperationError, MalformedDocumentError
from .models import (
    AuditReadReport,
    RegistryDocument,
    RepositoryRecord,
    RepositoryStatus,
    ValidationIssue,
)
from .paths import RegistryPaths
from .storage import JsonDocumentStore
from .validation import validate_registry_document


def _file_issue(path: Path, label: str) -> ValidationIssue | None:
    try:
        if not path.exists():
            return ValidationIssue(str(path), "missing-file", f"{label} is missing")
        if not path.is_file():
            return ValidationIssue(str(path), "not-file", f"{label} is not a file")
        path.read_bytes()
    except OSError as error:
        return ValidationIssue(str(path), "unreadable-file", f"{label} is unreadable: {error}")
    return None


def _directory_issue(path: Path, label: str) -> ValidationIssue | None:
    try:
        if not path.exists():
            return ValidationIssue(str(path), "missing-directory", f"{label} is missing")
        if not path.is_dir():
            return ValidationIssue(str(path), "not-directory", f"{label} is not a directory")
        tuple(path.iterdir())
    except OSError as error:
        return ValidationIssue(
            str(path), "unreadable-directory", f"{label} is unreadable: {error}"
        )
    return None


def _registry_health(paths: RegistryPaths, store: JsonDocumentStore) -> tuple[ValidationIssue, ...]:
    issue = _file_issue(paths.registry_file, "registry file")
    if issue is not None:
        return (issue,)
    try:
        document = store.read(paths.registry_file)
    except MalformedDocumentError as error:
        return (ValidationIssue(str(paths.registry_file), "json", str(error)),)
    except OSError as error:
        return (
            ValidationIssue(
                str(paths.registry_file),
                "unreadable-file",
                f"registry file is unreadable: {error}",
            ),
        )
    return validate_registry_document(document, paths).issues


def _managed_file_issues(paths: RegistryPaths) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    for path, label in (
        (paths.readme, "README.md"),
        (paths.changelog, "CHANGELOG.md"),
        (paths.skills_dir / "manifest.json", "skills manifest"),
        (paths.hooks_dir / "manifest.json", "hooks manifest"),
    ):
        issue = _file_issue(path, label)
        if issue is not None:
            issues.append(issue)
    return tuple(issues)


def root_health(paths: RegistryPaths, store: JsonDocumentStore) -> tuple[ValidationIssue, ...]:
    """Return strict root schema and managed global tree health issues."""
    issues = list(_registry_health(paths, store))
    issues.extend(_managed_file_issues(paths))
    repos_issue = _directory_issue(paths.repos_dir, "repositories directory")
    if repos_issue is not None:
        issues.append(repos_issue)
    return tuple(issues)


def _find_record(registry: RegistryDocument, repository_id: str) -> RepositoryRecord:
    for record in registry.repositories:
        if record.id == repository_id:
            return record
    raise InvalidOperationError(f"unknown repository id: {repository_id}")


def audit_selection(
    registry: RegistryDocument, repository_id: str | None
) -> tuple[RepositoryRecord, ...]:
    """Select one requested record or all active records in ID order."""
    if repository_id is not None:
        return (_find_record(registry, repository_id),)
    return tuple(
        sorted(
            (record for record in registry.repositories if record.status is RepositoryStatus.ACTIVE),
            key=lambda record: record.id,
        )
    )


def read_audit(
    paths: RegistryPaths,
    records: tuple[RepositoryRecord, ...],
    repository_id: str | None = None,
) -> AuditReadReport:
    """Read selected global audit files and aggregate events and issues."""
    events = []
    issues = []
    for record in records:
        report = AuditEventStore(paths.repository(record.id).changes_audit).read(repository_id)
        events.extend(report.events)
        issues.extend(report.issues)
    return AuditReadReport(tuple(events), tuple(issues))
