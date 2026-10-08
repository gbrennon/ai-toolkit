from dataclasses import dataclass
from pathlib import Path

from .dependencies import (
    load_hooks,
    load_skills,
    parse_hook_manifest,
    parse_skill_manifest,
)
from .errors import InvalidOperationError, MissingOriginError, RegistryError
from .git import GitResolver
from .git_port import GitPort
from .hashing import Sha256Digest
from .identity import (
    RemoteIdentity,
    choose_repository_id,
    normalize_remote,
    normalize_repository_id,
)
from .json_document_store import JsonDocumentStore
from .markdown import validate_agent_markdown
from .models import (
    DiscoveryResult,
    RegistryDocument,
    RepositoryRecord,
    RepositoryStatus,
    ValidationIssue,
    ValidationReport,
)
from .paths import RegistryPaths
from .repository_paths import RepositoryPaths
from .validation import parse_registry_document


@dataclass(frozen=True, slots=True, init=False)
class DiscoveryService:
    """Resolve and validate global agent configuration for one Git worktree."""

    _paths: RegistryPaths
    _git: GitPort
    _store: JsonDocumentStore

    def __init__(
        self,
        paths: RegistryPaths,
        git: GitPort | None = None,
        store: JsonDocumentStore | None = None,
    ) -> None:
        object.__setattr__(self, "_paths", paths)
        object.__setattr__(self, "_git", GitResolver() if git is None else git)
        object.__setattr__(
            self, "_store", JsonDocumentStore() if store is None else store
        )

    def discover(self, repository_path: Path | str) -> DiscoveryResult:
        """Resolve one worktree and validate only its global registry artifacts."""
        root = self._git.resolve_worktree_root(Path(repository_path)).resolve()
        remote = self._resolve_origin(root)
        registry = self._load_registry()
        record = self._select_record(registry, root, remote)
        report = self._validate_artifacts(record, registry.schema_version)
        return DiscoveryResult(record.repository_id, record.agent_config_path, report)

    def _load_registry(self) -> RegistryDocument:
        try:
            value = self._store.read(self._paths.registry_file)
        except (FileNotFoundError, OSError) as error:
            raise InvalidOperationError(
                f"registry is not initialized or cannot be read: {self._paths.registry_file}"
            ) from error
        return parse_registry_document(value, self._paths)

    def _resolve_origin(self, root: Path) -> RemoteIdentity | None:
        try:
            remote_name = self._git.canonical_remote(root)
            if remote_name != "origin":
                raise InvalidOperationError(
                    "discovery only supports the canonical origin remote"
                )
            return normalize_remote(self._git.remote_url(root, "origin"))
        except MissingOriginError:
            return None

    def _select_record(
        self,
        registry: RegistryDocument,
        root: Path,
        remote: RemoteIdentity | None,
    ) -> RepositoryRecord:
        if remote is None:
            return self._select_local_record(registry, root)
        return self._select_remote_record(registry, root, remote)

    def _select_local_record(
        self,
        registry: RegistryDocument,
        root: Path,
    ) -> RepositoryRecord:
        matching = self._local_matches(registry, root)
        active = self._active_records(matching)
        if len(active) == 1:
            return active[0]
        if len(active) > 1:
            raise InvalidOperationError(
                f"ambiguous active local path mapping for {root}"
            )
        if matching:
            raise InvalidOperationError(f"local path mapping for {root} is inactive")
        raise InvalidOperationError(f"no active registry mapping for local path {root}")

    def _local_matches(
        self,
        registry: RegistryDocument,
        root: Path,
    ) -> tuple[RepositoryRecord, ...]:
        return tuple(
            record for record in registry.repositories if record.local_path == root
        )

    def _active_records(
        self,
        records: tuple[RepositoryRecord, ...],
    ) -> tuple[RepositoryRecord, ...]:
        return tuple(
            record for record in records if record.status is RepositoryStatus.ACTIVE
        )

    def _select_remote_record(
        self,
        registry: RegistryDocument,
        root: Path,
        remote: RemoteIdentity,
    ) -> RepositoryRecord:
        remote_matches = self._remote_matches(registry, remote)
        if len(remote_matches) > 1:
            raise InvalidOperationError(
                f"ambiguous normalized remote mapping for {remote.normalized}"
            )
        if remote_matches:
            record = remote_matches[0]
            self._require_active(record)
            self._require_identity(record, remote)
            self._require_local_path(record, root)
            return record
        candidate_id = choose_repository_id(
            remote,
            (
                (record.repository_id, record.git_remote)
                for record in registry.repositories
            ),
        )
        candidate = self._record_by_id(registry, candidate_id)
        if candidate is None:
            raise InvalidOperationError(
                f"no active registry mapping for normalized remote {remote.normalized}"
            )
        self._require_active(candidate)
        raise InvalidOperationError(
            f"registry mapping for {candidate.repository_id} disagrees with remote {remote.normalized}"
        )

    def _remote_matches(
        self,
        registry: RegistryDocument,
        remote: RemoteIdentity,
    ) -> tuple[RepositoryRecord, ...]:
        return tuple(
            record
            for record in registry.repositories
            if normalize_remote(record.git_remote) == remote
        )

    def _record_by_id(
        self,
        registry: RegistryDocument,
        repository_id: str,
    ) -> RepositoryRecord | None:
        return next(
            (
                record
                for record in registry.repositories
                if record.repository_id == repository_id
            ),
            None,
        )

    def _require_active(self, record: RepositoryRecord) -> None:
        if record.status is not RepositoryStatus.ACTIVE:
            raise InvalidOperationError(
                f"registry mapping for {record.repository_id} is inactive"
            )

    def _require_identity(
        self, record: RepositoryRecord, remote: RemoteIdentity
    ) -> None:
        base = normalize_repository_id(remote.repository)
        qualified = normalize_repository_id(f"{remote.owner.replace('/', '-')}-{base}")
        if record.repository_id not in {base, qualified}:
            raise InvalidOperationError(
                f"registry mapping id {record.repository_id} does not match remote {remote.normalized}"
            )

    def _require_local_path(self, record: RepositoryRecord, root: Path) -> None:
        if record.local_path != root:
            raise InvalidOperationError(
                f"registry mapping local path {record.local_path} disagrees with Git root {root}"
            )

    def _validate_artifacts(
        self, record: RepositoryRecord, schema_version: int
    ) -> ValidationReport:
        issues: list[ValidationIssue] = []
        repository = self._paths.repository(record.repository_id)
        if record.agent_config_path != repository.agent_config:
            issues.append(
                ValidationIssue(
                    "agentConfigPath",
                    "path-containment",
                    "agentConfigPath must be the repository ID's global AGENT.md",
                )
            )
        self._validate_agent(record, schema_version, issues)
        self._validate_metadata(record, repository, issues)
        self._validate_dependencies(repository, issues)
        return ValidationReport(tuple(issues))

    def _validate_agent(
        self,
        record: RepositoryRecord,
        schema_version: int,
        issues: list[ValidationIssue],
    ) -> None:
        try:
            content_bytes = record.agent_config_path.read_bytes()
        except FileNotFoundError, IsADirectoryError, OSError:
            issues.append(
                ValidationIssue("agentConfigPath", "missing", "AGENT.md is unreadable")
            )
            return
        if Sha256Digest.digest_bytes(content_bytes) != record.config_sha256:
            issues.append(
                ValidationIssue(
                    "configSha256",
                    "digest",
                    "AGENT.md bytes do not match configSha256",
                )
            )
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            issues.append(ValidationIssue("AGENT.md", "encoding", str(error)))
            return
        issues.extend(validate_agent_markdown(content, record, schema_version).issues)

    def _validate_metadata(
        self,
        record: RepositoryRecord,
        repository: RepositoryPaths,
        issues: list[ValidationIssue],
    ) -> None:
        try:
            metadata = self._store.read(repository.metadata)
        except (OSError, RegistryError) as error:
            issues.append(ValidationIssue("metadata", "metadata", str(error)))
            return
        if metadata != record.to_json():
            issues.append(
                ValidationIssue(
                    "metadata", "metadata", "metadata does not match registry record"
                )
            )

    def _validate_dependencies(
        self,
        repository: RepositoryPaths,
        issues: list[ValidationIssue],
    ) -> None:
        try:
            skill_references = parse_skill_manifest(self._store.read(repository.skills))
            load_skills(skill_references, self._paths)
        except (OSError, RegistryError) as error:
            issues.append(ValidationIssue("skills", "dependencies", str(error)))
        try:
            hook_references = parse_hook_manifest(self._store.read(repository.hooks))
            load_hooks(hook_references, self._paths)
        except (OSError, RegistryError) as error:
            issues.append(ValidationIssue("hooks", "dependencies", str(error)))
