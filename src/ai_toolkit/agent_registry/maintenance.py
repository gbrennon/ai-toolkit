from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from .audit import AuditEventStore
from .dependencies import load_hooks, load_skills, parse_hook_manifest, parse_skill_manifest
from .errors import MalformedDocumentError, RegistryError
from .hashing import Sha256Digest
from .json_document_store import JsonDocumentStore, JsonValue
from .markdown import validate_agent_markdown
from .models import RepositoryRecord, ValidationIssue, ValidationReport
from .paths import RegistryPaths
from .repository_paths import RepositoryPaths
from .validation import parse_repository_record, validate_registry_document


def validate_registry(paths: RegistryPaths, store: JsonDocumentStore) -> ValidationReport:
    """Validate the registry document and every managed repository artifact."""
    try:
        document = store.read(paths.registry_file)
    except MalformedDocumentError as error:
        return ValidationReport(
            (ValidationIssue(str(paths.registry_file), "json", str(error)),)
        )
    except FileNotFoundError as error:
        return ValidationReport(
            (ValidationIssue(str(paths.registry_file), "missing", str(error)),)
        )
    except OSError as error:
        return ValidationReport(
            (ValidationIssue(str(paths.registry_file), "unreadable", str(error)),)
        )

    root_report = validate_registry_document(document, paths)
    artifact_issues = _artifact_issues(document, paths, store)
    return ValidationReport(root_report.issues + artifact_issues)


def _artifact_issues(
    document: JsonValue, paths: RegistryPaths, store: JsonDocumentStore
) -> tuple[ValidationIssue, ...]:
    if not isinstance(document, Mapping):
        return ()
    raw_records = document.get("repositories")
    if not _is_sequence(raw_records):
        return ()
    issues: list[ValidationIssue] = []
    for index, raw_record in enumerate(cast(Sequence[object], raw_records)):
        record = _parse_record(raw_record, paths)
        if record is not None:
            issues.extend(_record_artifact_issues(index, record, paths, store))
    return tuple(issues)


def _parse_record(raw_record: object, paths: RegistryPaths) -> RepositoryRecord | None:
    try:
        return parse_repository_record(raw_record, paths)
    except RegistryError:
        return None


def _record_artifact_issues(
    index: int,
    record: RepositoryRecord,
    paths: RegistryPaths,
    store: JsonDocumentStore,
) -> tuple[ValidationIssue, ...]:
    prefix = f"repositories[{index}]"
    try:
        repository = paths.repository(record.repository_id)
    except RegistryError as error:
        return (ValidationIssue(f"{prefix}.id", "path", str(error)),)
    issues: list[ValidationIssue] = []
    if record.agent_config_path != repository.agent_config:
        issues.append(
            ValidationIssue(
                f"{prefix}.agentConfigPath",
                "path",
                "agentConfigPath does not match repository id",
            )
        )
    issues.extend(_agent_issues(repository.agent_config, record))
    issues.extend(_metadata_issues(repository, record, store))
    issues.extend(_skills_issues(repository.skills, paths, store))
    issues.extend(_hooks_issues(repository.hooks, paths, store))
    issues.extend(_audit_issues(repository, record.repository_id))
    return tuple(issues)


def _agent_issues(path: Path, record: RepositoryRecord) -> tuple[ValidationIssue, ...]:
    try:
        content = path.read_bytes()
    except FileNotFoundError as error:
        return (_missing(path, error),)
    except OSError as error:
        return (_unreadable(path, error),)
    issues: list[ValidationIssue] = []
    if Sha256Digest.digest_bytes(content) != record.config_sha256:
        issues.append(
            ValidationIssue(str(path), "digest", "AGENT.md digest does not match record")
        )
    return tuple(issues) + _markdown_issues(content, path, record)


def _markdown_issues(
    content: bytes, path: Path, record: RepositoryRecord
) -> tuple[ValidationIssue, ...]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        return (ValidationIssue(str(path), "markdown", str(error)),)
    report = validate_agent_markdown(text, record)
    return tuple(
        ValidationIssue(f"{path}:{issue.field}", issue.code, issue.message)
        for issue in report.issues
    )


def _metadata_issues(
    repository: RepositoryPaths, record: RepositoryRecord, store: JsonDocumentStore
) -> tuple[ValidationIssue, ...]:
    try:
        metadata = store.read(repository.metadata)
    except FileNotFoundError as error:
        return (_missing(repository.metadata, error),)
    except (MalformedDocumentError, OSError) as error:
        return (ValidationIssue(str(repository.metadata), "metadata", str(error)),)
    if metadata != record.to_json():
        return (
            ValidationIssue(
                str(repository.metadata), "metadata", "metadata does not match record"
            ),
        )
    return ()


def _skills_issues(
    path: Path, paths: RegistryPaths, store: JsonDocumentStore
) -> tuple[ValidationIssue, ...]:
    try:
        manifest = store.read(path)
        references = parse_skill_manifest(manifest)
        load_skills(references, paths)
    except FileNotFoundError as error:
        return (_missing(path, error),)
    except (OSError, RegistryError) as error:
        return (ValidationIssue(str(path), "skills", str(error)),)
    return ()


def _hooks_issues(
    path: Path, paths: RegistryPaths, store: JsonDocumentStore
) -> tuple[ValidationIssue, ...]:
    try:
        manifest = store.read(path)
        references = parse_hook_manifest(manifest)
        load_hooks(references, paths)
    except FileNotFoundError as error:
        return (_missing(path, error),)
    except (OSError, RegistryError) as error:
        return (ValidationIssue(str(path), "hooks", str(error)),)
    return ()


def _audit_issues(repository: RepositoryPaths, repository_id: str) -> tuple[ValidationIssue, ...]:
    path = repository.changes_audit
    if not path.is_file():
        return (_missing(path, FileNotFoundError(path)),)
    try:
        report = AuditEventStore(path).read(repository_id)
    except (OSError, RegistryError) as error:
        return (ValidationIssue(str(path), "audit", str(error)),)
    return report.issues


def _missing(path: Path, error: BaseException) -> ValidationIssue:
    return ValidationIssue(str(path), "missing", f"artifact is missing: {error}")


def _unreadable(path: Path, error: BaseException) -> ValidationIssue:
    return ValidationIssue(str(path), "unreadable", f"artifact is unreadable: {error}")


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
