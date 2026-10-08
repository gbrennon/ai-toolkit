from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .audit import AuditEventStore
from .errors import InvalidOperationError
from .hashing import Sha256Digest
from .identity import normalize_remote
from .models import AuditEvent, RegistryDocument, RepositoryRecord, RepositoryStatus
from .paths import RegistryPaths
from .repository_paths import RepositoryPaths
from .service_helpers import same_path, validate_existing
from .migration_storage import (
    backup_repository,
    restore_file,
    restore_repository,
    snapshot_file,
)
from .storage import AtomicWriter, JsonDocumentStore
from .validation import parse_registry_document

Clock = Callable[[], datetime]
MigrationRequest = tuple[str, str | None, Path | None, Clock]


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    """Immutable staged state used to publish and roll back one migration."""

    paths: RegistryPaths
    repository: RepositoryPaths
    old_record: RepositoryRecord
    record: RepositoryRecord
    registry: RegistryDocument
    content: str
    changelog: str
    backup: Path
    registry_snapshot: tuple[bytes, int] | None
    changelog_snapshot: tuple[bytes, int] | None


def update_agent_content(content: str, remote: str, local_path: Path) -> str:
    """Update managed identity references while preserving policy text."""
    replacements = {
        "gitRemote:": f"gitRemote: {remote}",
        "- Git remote:": f"- Git remote: {remote}",
        "- Local path:": f"- Local path: {local_path}",
    }
    trailing_newline = content.endswith("\n")
    lines = content.splitlines()
    updated = [
        next(
            (
                replacement
                for prefix, replacement in replacements.items()
                if line.startswith(prefix)
            ),
            line,
        )
        for line in lines
    ]
    result = "\n".join(updated)
    return result + ("\n" if trailing_newline else "")


def changelog_entry(
    existing: str,
    instant: datetime,
    old_record: RepositoryRecord,
    new_record: RepositoryRecord,
) -> str:
    """Append one deterministic migration entry to the registry changelog."""
    line = (
        f"- {instant.isoformat().replace('+00:00', 'Z')} migrate {new_record.id}: "
        f"remote {old_record.git_remote} -> {new_record.git_remote}; "
        f"local path {old_record.local_path} -> {new_record.local_path}.\n"
    )
    separator = "" if existing.endswith("\n") else "\n"
    return existing + separator + line


def apply_migration(
    paths: RegistryPaths, store: JsonDocumentStore, request: MigrationRequest
) -> RepositoryRecord:
    """Migrate active global registry identity metadata with rollback."""
    plan = _prepare_migration(paths, store, request)
    try:
        _publish_migration(plan, store)
        validate_existing(plan.record, paths)
        return plan.record
    except Exception:
        _rollback_migration(plan)
        raise


def _prepare_migration(
    paths: RegistryPaths, store: JsonDocumentStore, request: MigrationRequest
) -> MigrationPlan:
    repository_id, git_remote, local_path, clock = request
    registry = _read_registry(paths, store)
    old_record = _find_active_record(registry, repository_id)
    validate_existing(old_record, paths)
    remote = _normalize_remote(git_remote, old_record.git_remote)
    local = _normalize_local_path(local_path, old_record.local_path)
    _check_collisions(registry.repositories, old_record, remote, local)
    repository = paths.repository(repository_id)
    content = update_agent_content(
        repository.agent_config.read_text(encoding="utf-8"), remote, local
    )
    instant = _utc_clock(clock)
    record = RepositoryRecord(
        old_record.repository_id,
        remote,
        local,
        old_record.agent_config_path,
        Sha256Digest.digest_bytes(content.encode("utf-8")),
        old_record.status,
        old_record.registered_at,
        instant,
    )
    updated = _updated_registry(registry, repository_id, record, instant)
    return MigrationPlan(
        paths,
        repository,
        old_record,
        record,
        updated,
        content,
        paths.changelog.read_text(encoding="utf-8"),
        backup_repository(repository.directory, paths.root, repository_id),
        snapshot_file(paths.registry_file),
        snapshot_file(paths.changelog),
    )


def _updated_registry(
    registry: RegistryDocument,
    repository_id: str,
    record: RepositoryRecord,
    instant: datetime,
) -> RegistryDocument:
    records = tuple(
        sorted(
            (
                record if item.repository_id == repository_id else item
                for item in registry.repositories
            ),
            key=lambda item: item.repository_id,
        )
    )
    return RegistryDocument(
        registry.schema_version, registry.registry_version, instant, records
    )


def _publish_migration(plan: MigrationPlan, store: JsonDocumentStore) -> None:
    JsonDocumentStore().write(plan.repository.metadata, plan.record.to_json())
    AtomicWriter().write_text(plan.repository.agent_config, plan.content)
    store.write(plan.paths.registry_file, plan.registry.to_json())
    AuditEventStore(plan.repository.changes_audit).append(
        AuditEvent(
            plan.registry.updated_at,
            "migrate",
            plan.record.id,
            "1",
            "success",
            0.0,
            {
                "oldRemote": plan.old_record.git_remote,
                "newRemote": plan.record.git_remote,
                "oldLocalPath": str(plan.old_record.local_path),
                "newLocalPath": str(plan.record.local_path),
            },
        )
    )
    AtomicWriter().write_text(
        plan.paths.changelog,
        changelog_entry(
            plan.changelog,
            plan.registry.updated_at,
            plan.old_record,
            plan.record,
        ),
    )


def _rollback_migration(plan: MigrationPlan) -> None:
    try:
        restore_repository(plan.backup, plan.repository.directory)
        restore_file(plan.paths.registry_file, plan.registry_snapshot)
        restore_file(plan.paths.changelog, plan.changelog_snapshot)
    except Exception as error:
        raise InvalidOperationError(
            f"migration rollback failed for {plan.record.id}"
        ) from error


def _read_registry(paths: RegistryPaths, store: JsonDocumentStore) -> RegistryDocument:
    try:
        return parse_registry_document(store.read(paths.registry_file), paths)
    except Exception as error:
        raise InvalidOperationError(
            f"registry is not initialized or valid: {paths.registry_file}"
        ) from error


def _find_active_record(
    registry: RegistryDocument, repository_id: str
) -> RepositoryRecord:
    record = next(
        (item for item in registry.repositories if item.repository_id == repository_id),
        None,
    )
    if record is None:
        raise InvalidOperationError(f"repository is not registered: {repository_id}")
    if record.status is not RepositoryStatus.ACTIVE:
        raise InvalidOperationError(f"repository is not active: {repository_id}")
    return record


def _normalize_remote(value: str | None, existing: str) -> str:
    if value is None:
        return existing
    try:
        return normalize_remote(value).canonical_url
    except Exception as error:
        raise InvalidOperationError(f"invalid git remote: {value!r}") from error


def _normalize_local_path(value: Path | None, existing: Path) -> Path:
    if value is None:
        return existing
    try:
        return Path(value).expanduser().resolve()
    except (OSError, TypeError, ValueError) as error:
        raise InvalidOperationError(f"invalid local path: {value!r}") from error


def _check_collisions(
    records: tuple[RepositoryRecord, ...],
    current: RepositoryRecord,
    remote: str,
    local: Path,
) -> None:
    others = tuple(record for record in records if record.id != current.id)
    if _has_remote_collision(others, remote):
        raise InvalidOperationError("normalized remote is already registered")
    if _has_local_collision(others, local):
        raise InvalidOperationError("active local path is already registered")


def _has_remote_collision(records: tuple[RepositoryRecord, ...], remote: str) -> bool:
    normalized = normalize_remote(remote)
    return any(normalize_remote(record.git_remote) == normalized for record in records)


def _has_local_collision(records: tuple[RepositoryRecord, ...], local: Path) -> bool:
    return any(
        record.status is RepositoryStatus.ACTIVE and same_path(record.local_path, local)
        for record in records
    )


def _utc_clock(clock: Clock) -> datetime:
    instant = clock()
    if instant.tzinfo is None:
        raise InvalidOperationError(
            "registry clock must return a timezone-aware datetime"
        )
    return instant.astimezone(timezone.utc)
