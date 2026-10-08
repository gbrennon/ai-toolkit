from collections.abc import Mapping, Sequence
from datetime import datetime
import re
from pathlib import Path
from typing import cast

from .errors import MalformedDocumentError, RegistryError, SchemaValidationError
from .identity import RemoteIdentity, normalize_remote
from .models import (
    RegistryDocument,
    RepositoryRecord,
    RepositoryStatus,
    ValidationIssue,
    ValidationReport,
)
from .paths import RegistryPaths
from .storage import JsonDocumentStore

_SCHEMA_VERSION = 1
_RECORD_FIELDS = frozenset({
    "id", "gitRemote", "localPath", "agentConfigPath", "configSha256", "status",
    "registeredAt", "updatedAt",
})
_ROOT_FIELDS = frozenset({"schemaVersion", "registryVersion", "updatedAt", "repositories"})
_SHA256 = re.compile(r"[0-9a-f]{64}")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def validate_registry_document(value: object, paths: RegistryPaths | None = None) -> ValidationReport:
    """Collect every independent schema and cross-record registry issue."""
    selected_paths = RegistryPaths() if paths is None else paths
    if not isinstance(value, Mapping):
        return ValidationReport((ValidationIssue("root", "type", "root must be an object"),))
    issues = _root_issues(value)
    record_issues, records = _validated_records(value.get("repositories"), selected_paths)
    issues.extend(record_issues)
    issues.extend(_duplicate_issues(records))
    return ValidationReport(tuple(issues))

def _validated_records(value: object, paths: RegistryPaths) -> tuple[list[ValidationIssue], list[RepositoryRecord]]:
    if not _is_sequence(value):
        return [ValidationIssue("repositories", "type", "repositories must be an array")], []
    issues: list[ValidationIssue] = []
    records: list[RepositoryRecord] = []
    for index, raw_record in enumerate(cast(Sequence[object], value)):
        record, record_issues = _parse_record(raw_record, index, paths)
        issues.extend(record_issues)
        if record is not None:
            records.append(record)
    return issues, records


def parse_registry_document(value: object, paths: RegistryPaths | None = None) -> RegistryDocument:
    """Parse a valid external registry object or raise a schema error."""
    selected_paths = RegistryPaths() if paths is None else paths
    report = validate_registry_document(value, selected_paths)
    if not report.is_valid:
        raise SchemaValidationError(_format_report(report))
    mapping = cast(Mapping[str, object], value)
    records = tuple(_record_from_mapping(cast(Mapping[str, object], item)) for item in cast(Sequence[object], mapping["repositories"]))
    updated_at = parse_utc_timestamp(cast(str, mapping["updatedAt"]))
    if updated_at is None:
        raise SchemaValidationError("updatedAt is not a valid UTC timestamp")
    return RegistryDocument(cast(int, mapping["schemaVersion"]), cast(str, mapping["registryVersion"]), updated_at, records)


def validate_registry_file(path: Path, paths: RegistryPaths | None = None) -> ValidationReport:
    """Read and validate one registry JSON file."""
    try:
        document = JsonDocumentStore().read(path)
    except MalformedDocumentError as error:
        return ValidationReport((ValidationIssue(str(path), "json", str(error)),))
    return validate_registry_document(document, paths)

def validate_repository_record(value: object, paths: RegistryPaths | None = None) -> ValidationReport:
    """Validate one registry record independently of the root document."""
    selected_paths = RegistryPaths() if paths is None else paths
    _, issues = _parse_record(value, 0, selected_paths)
    return ValidationReport(issues)


def parse_repository_record(value: object, paths: RegistryPaths | None = None) -> RepositoryRecord:
    """Parse one valid registry record or raise a schema error."""
    selected_paths = RegistryPaths() if paths is None else paths
    record, issues = _parse_record(value, 0, selected_paths)
    if record is None or issues:
        raise SchemaValidationError(_format_report(ValidationReport(issues)))
    return record


def parse_utc_timestamp(value: str) -> datetime | None:
    """Parse an exact UTC timestamp with a trailing Z."""
    if _TIMESTAMP.fullmatch(value) is None:
        return None
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None


def _root_issues(value: Mapping[str, object]) -> list[ValidationIssue]:
    issues = _unknown_fields(value, _ROOT_FIELDS, "root")
    _check_schema(value, issues)
    _check_text(value, "registryVersion", issues)
    _check_timestamp(value, "updatedAt", issues)
    return issues


def _parse_record(value: object, index: int, paths: RegistryPaths) -> tuple[RepositoryRecord | None, tuple[ValidationIssue, ...]]:
    prefix = f"repositories[{index}]"
    if not isinstance(value, Mapping):
        return None, (ValidationIssue(prefix, "type", "record must be an object"),)
    checks: dict[str, object | None] = {field: value.get(field) for field in _RECORD_FIELDS}
    issues = _unknown_fields(value, _RECORD_FIELDS, prefix)
    _check_record_text(checks, "id", issues, prefix)
    _check_remote(checks, issues, prefix)
    local_path = _check_absolute_path(checks, "localPath", issues, prefix)
    agent_path = _check_agent_path(checks, "agentConfigPath", paths, issues, prefix)
    _check_digest(checks, issues, prefix)
    _check_status(checks, issues, prefix)
    checks["registeredAt"] = _check_timestamp(value, "registeredAt", issues, prefix)
    checks["updatedAt"] = _check_timestamp(value, "updatedAt", issues, prefix)
    if issues:
        return None, tuple(issues)
    return _record_from_checks(checks, local_path, agent_path), ()


def _record_from_checks(checks: Mapping[str, object | None], local_path: Path | None, agent_path: Path | None) -> RepositoryRecord:
    return RepositoryRecord(
        cast(str, checks["id"]), cast(str, checks["gitRemote"]), cast(Path, local_path), cast(Path, agent_path),
        cast(str, checks["configSha256"]), cast(RepositoryStatus, checks["status"]),
        cast(datetime, checks["registeredAt"]), cast(datetime, checks["updatedAt"]),
    )


def _record_from_mapping(value: Mapping[str, object]) -> RepositoryRecord:
    registered_at = parse_utc_timestamp(cast(str, value["registeredAt"]))
    updated_at = parse_utc_timestamp(cast(str, value["updatedAt"]))
    if registered_at is None or updated_at is None:
        raise SchemaValidationError("record timestamp failed validation")
    return RepositoryRecord(
        cast(str, value["id"]), cast(str, value["gitRemote"]), Path(cast(str, value["localPath"])),
        Path(cast(str, value["agentConfigPath"])), cast(str, value["configSha256"]),
        RepositoryStatus(cast(str, value["status"])), registered_at, updated_at,
    )


def _unknown_fields(value: Mapping[str, object], allowed: frozenset[str], prefix: str) -> list[ValidationIssue]:
    return [ValidationIssue(f"{prefix}.{key}", "unknown-field", "field is not allowed") for key in value if key not in allowed]


def _check_schema(value: Mapping[str, object], issues: list[ValidationIssue]) -> None:
    if value.get("schemaVersion") != _SCHEMA_VERSION or isinstance(value.get("schemaVersion"), bool):
        issues.append(ValidationIssue("schemaVersion", "schema-version", "schemaVersion must be 1"))


def _check_text(value: Mapping[str, object], field: str, issues: list[ValidationIssue]) -> None:
    if not isinstance(value.get(field), str) or not cast(str, value[field]).strip():
        issues.append(ValidationIssue(field, "required", f"{field} must be nonempty text"))


def _check_record_text(checks: Mapping[str, object | None], field: str, issues: list[ValidationIssue], prefix: str) -> None:
    value = checks[field]
    if not isinstance(value, str) or not value.strip():
        issues.append(ValidationIssue(f"{prefix}.{field}", "required", "field must be nonempty text"))


def _check_remote(checks: Mapping[str, object | None], issues: list[ValidationIssue], prefix: str) -> None:
    value = checks["gitRemote"]
    if not isinstance(value, str) or not value.strip():
        issues.append(ValidationIssue(f"{prefix}.gitRemote", "remote", "gitRemote must be nonempty"))
        return
    try:
        normalize_remote(value)
    except (ValueError, RegistryError) as error:
        issues.append(ValidationIssue(f"{prefix}.gitRemote", "remote", str(error)))


def _check_timestamp(value: Mapping[str, object], field: str, issues: list[ValidationIssue], prefix: str = "") -> datetime | None:
    raw = value.get(field)
    parsed = parse_utc_timestamp(raw) if isinstance(raw, str) else None
    if parsed is None:
        name = f"{prefix}.{field}" if prefix else field
        issues.append(ValidationIssue(name, "timestamp", "timestamp must be UTC with a Z suffix"))
    return parsed


def _check_absolute_path(checks: Mapping[str, object | None], field: str, issues: list[ValidationIssue], prefix: str) -> Path | None:
    raw = checks[field]
    path = Path(raw) if isinstance(raw, str) else None
    if path is None or not path.is_absolute() or path != path.resolve():
        issues.append(ValidationIssue(f"{prefix}.{field}", "path", "path must be absolute and resolved"))
        return None
    return path


def _check_agent_path(checks: Mapping[str, object | None], field: str, paths: RegistryPaths, issues: list[ValidationIssue], prefix: str) -> Path | None:
    path = _check_absolute_path(checks, field, issues, prefix)
    if path is None:
        return None
    if path.name != "AGENT.md" or not path.is_relative_to(paths.repos_dir.resolve()):
        issues.append(ValidationIssue(f"{prefix}.{field}", "path-containment", "agentConfigPath must be below repos and end AGENT.md"))
    return path


def _check_digest(checks: Mapping[str, object | None], issues: list[ValidationIssue], prefix: str) -> None:
    if not isinstance(checks["configSha256"], str) or _SHA256.fullmatch(cast(str, checks["configSha256"])) is None:
        issues.append(ValidationIssue(f"{prefix}.configSha256", "digest", "configSha256 must be 64 lowercase hex characters"))


def _check_status(checks: dict[str, object | None], issues: list[ValidationIssue], prefix: str) -> None:
    try:
        checks["status"] = RepositoryStatus(cast(str, checks["status"]))
    except (TypeError, ValueError):
        issues.append(ValidationIssue(f"{prefix}.status", "status", "status must be active, archived, or blocked"))


def _duplicate_issues(records: Sequence[RepositoryRecord]) -> tuple[ValidationIssue, ...]:
    return tuple(_duplicate_ids(records) + _duplicate_remotes(records) + _duplicate_paths(records))


def _duplicate_ids(records: Sequence[RepositoryRecord]) -> list[ValidationIssue]:
    seen: set[str] = set()
    issues: list[ValidationIssue] = []
    for record in records:
        if record.repository_id in seen:
            issues.append(ValidationIssue("repositories", "duplicate-id", f"duplicate repository id {record.repository_id}"))
        seen.add(record.repository_id)
    return issues


def _duplicate_remotes(records: Sequence[RepositoryRecord]) -> list[ValidationIssue]:
    seen: set[RemoteIdentity] = set()
    issues: list[ValidationIssue] = []
    for record in records:
        try:
            remote = normalize_remote(record.git_remote)
        except (ValueError, RegistryError):
            continue
        if remote in seen:
            issues.append(ValidationIssue("repositories", "duplicate-remote", f"duplicate remote {remote.normalized}"))
        seen.add(remote)
    return issues


def _duplicate_paths(records: Sequence[RepositoryRecord]) -> list[ValidationIssue]:
    seen: set[Path] = set()
    issues: list[ValidationIssue] = []
    for record in records:
        if record.status is not RepositoryStatus.ACTIVE:
            continue
        if record.local_path in seen:
            issues.append(ValidationIssue("repositories", "duplicate-local-path", f"duplicate active path {record.local_path}"))
        seen.add(record.local_path)
    return issues


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _format_report(report: ValidationReport) -> str:
    return "; ".join(f"{issue.field}: {issue.message}" for issue in report.issues)
