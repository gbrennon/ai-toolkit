from collections.abc import Iterable
from pathlib import Path
import os
import shutil
from typing import NoReturn

from .dependencies import parse_hook_manifest, parse_skill_manifest
from .errors import IdentityCollisionError, InvalidOperationError, RegistryError
from .hashing import Sha256Digest
from .identity import RemoteIdentity, normalize_remote
from .markdown import validate_agent_markdown
from .models import RepositoryRecord, RepositoryStatus, ValidationReport
from .models._json import JsonValue
from .paths import RegistryPaths
from .repository_paths import RepositoryPaths
from .storage import AtomicWriter, JsonDocumentStore, NdjsonEventStore
from .validation import validate_repository_record


def report_message(report: ValidationReport) -> str:
    return "; ".join(f"{issue.field}: {issue.message}" for issue in report.issues)


def read_agent(root: Path) -> str:
    path = root / "AGENT.md"
    try:
        return path.read_bytes().decode("utf-8")
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError, OSError) as error:
        raise InvalidOperationError(
            f"resolved repository root has no readable AGENT.md: {path}"
        ) from error


def same_path(left: Path, right: Path) -> bool:
    return left.expanduser().resolve() == right.expanduser().resolve()


def same_identity(
    record: RepositoryRecord,
    remote: RemoteIdentity,
    root: Path,
    repository_id: str,
) -> bool:
    return (
        record.repository_id == repository_id
        and normalize_remote(record.git_remote) == remote
        and same_path(record.local_path, root)
        and record.status is RepositoryStatus.ACTIVE
    )


def read_existing_artifacts(
    repository: RepositoryPaths,
) -> tuple[str, JsonValue, JsonValue, JsonValue]:
    try:
        return (
            repository.agent_config.read_text(encoding="utf-8"),
            JsonDocumentStore().read(repository.metadata),
            JsonDocumentStore().read(repository.skills),
            JsonDocumentStore().read(repository.hooks),
        )
    except (OSError, RegistryError) as error:
        raise InvalidOperationError(
            f"existing repository artifacts are unreadable: {repository.directory}"
        ) from error


def validate_existing(record: RepositoryRecord, paths: RegistryPaths) -> None:
    report = validate_repository_record(record.to_json(), paths)
    if not report.is_valid:
        raise InvalidOperationError(
            f"existing record is invalid: {report_message(report)}"
        )
    repository = paths.repository(record.repository_id)
    _validate_existing_directory(repository)
    content, metadata, skills, hooks = read_existing_artifacts(repository)
    _validate_existing_content(record, content, metadata)
    _validate_existing_dependencies(repository, skills, hooks)


def _validate_existing_directory(repository: RepositoryPaths) -> None:
    if not repository.directory.is_dir():
        raise InvalidOperationError(
            f"existing repository directory is missing: {repository.directory}"
        )


def _validate_existing_content(
    record: RepositoryRecord, content: str, metadata: JsonValue
) -> None:
    if Sha256Digest.digest_bytes(content.encode("utf-8")) != record.config_sha256:
        raise InvalidOperationError(
            f"existing AGENT.md digest does not match {record.repository_id}"
        )
    markdown_report = validate_agent_markdown(content, record)
    if not markdown_report.is_valid:
        raise InvalidOperationError(
            f"existing AGENT.md is invalid: {report_message(markdown_report)}"
        )
    if metadata != record.to_json():
        raise InvalidOperationError(
            f"existing metadata does not match {record.repository_id}"
        )


def _validate_existing_dependencies(
    repository: RepositoryPaths, skills: JsonValue, hooks: JsonValue
) -> None:
    try:
        parse_skill_manifest(skills)
        parse_hook_manifest(hooks)
        NdjsonEventStore().read(repository.changes_audit)
    except RegistryError as error:
        raise InvalidOperationError(
            f"existing dependency artifacts are invalid: {error}"
        ) from error


def validate_collisions(
    records: Iterable[RepositoryRecord],
    candidate_id: str,
    remote: RemoteIdentity,
    root: Path,
) -> None:
    for record in records:
        same_local = same_path(record.local_path, root)
        _check_remote_collision(record, candidate_id, remote, same_local)
        _check_path_collision(record, candidate_id, same_local)
        _check_id_collision(record, candidate_id)


def _check_remote_collision(
    record: RepositoryRecord,
    candidate_id: str,
    remote: RemoteIdentity,
    same_local: bool,
) -> None:
    if normalize_remote(record.git_remote) != remote:
        return
    if (
        record.repository_id == candidate_id
        and same_local
        and record.status is RepositoryStatus.ACTIVE
    ):
        return
    raise IdentityCollisionError(
        candidate_id,
        f"normalized remote is already registered by {record.repository_id}",
    )


def _check_path_collision(
    record: RepositoryRecord, candidate_id: str, same_local: bool
) -> None:
    if record.status is RepositoryStatus.ACTIVE and same_local:
        raise IdentityCollisionError(
            candidate_id, "active local path is already registered"
        )


def _check_id_collision(record: RepositoryRecord, candidate_id: str) -> None:
    if record.repository_id == candidate_id:
        raise IdentityCollisionError(candidate_id, "repository ID is already mapped")


def _empty_manifest() -> dict[str, JsonValue]:
    return {"schemaVersion": 1, "entries": []}


def stage_repository(stage: Path, record: RepositoryRecord, content: str) -> Path:
    repository = RepositoryPaths(stage / record.repository_id)
    repository.directory.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        repository.directory.chmod(0o700)
    AtomicWriter().write_text(repository.agent_config, content)
    JsonDocumentStore().write(repository.metadata, record.to_json())
    JsonDocumentStore().write(repository.skills, _empty_manifest())
    JsonDocumentStore().write(repository.hooks, _empty_manifest())
    AtomicWriter().write_text(repository.changes_audit, "")
    validate_staged(repository, record)
    return repository.directory


def validate_staged(repository: RepositoryPaths, record: RepositoryRecord) -> None:
    content = repository.agent_config.read_text(encoding="utf-8")
    if Sha256Digest.digest_bytes(content.encode("utf-8")) != record.config_sha256:
        raise InvalidOperationError(
            "staged AGENT.md digest does not match registry record"
        )
    report = validate_agent_markdown(content, record)
    if not report.is_valid:
        raise InvalidOperationError(
            f"staged AGENT.md is invalid: {report_message(report)}"
        )
    metadata = JsonDocumentStore().read(repository.metadata)
    if metadata != record.to_json():
        raise InvalidOperationError("staged metadata does not match registry record")
    parse_skill_manifest(JsonDocumentStore().read(repository.skills))
    parse_hook_manifest(JsonDocumentStore().read(repository.hooks))
    NdjsonEventStore().read(repository.changes_audit)


def publish_repository(source: Path, destination: Path) -> None:
    if destination.exists():
        raise InvalidOperationError(
            f"repository directory already exists: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(source, destination)
    except OSError as error:
        raise InvalidOperationError(
            f"could not publish repository directory {destination}: {error}"
        ) from error


def remove_published(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def manifest_text() -> str:
    return '{\n  "entries": [],\n  "schemaVersion": 1\n}\n'


def raise_incompatible(path: Path, detail: str) -> NoReturn:
    raise InvalidOperationError(f"cannot initialize registry at {path}: {detail}")
