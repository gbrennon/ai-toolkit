from dataclasses import dataclass
from pathlib import Path

from .errors import InvalidOperationError
from .identity import (
    RemoteIdentity,
    choose_repository_id,
    normalize_remote,
    normalize_repository_id,
)
from .models import RegistryDocument, RepositoryRecord, RepositoryStatus


@dataclass(frozen=True, slots=True)
class RegistryRecordSelector:
    """Select the single active registry record that owns one Git worktree."""

    def select(
        self,
        registry: RegistryDocument,
        root: Path,
        remote: RemoteIdentity | None,
    ) -> RepositoryRecord:
        """Return the active record matching the worktree root or canonical remote."""
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
            return self._verified_remote_record(remote_matches[0], root, remote)
        return self._reject_unmatched_remote(registry, remote)

    def _verified_remote_record(
        self,
        record: RepositoryRecord,
        root: Path,
        remote: RemoteIdentity,
    ) -> RepositoryRecord:
        self._require_active(record)
        self._require_identity(record, remote)
        self._require_local_path(record, root)
        return record

    def _reject_unmatched_remote(
        self,
        registry: RegistryDocument,
        remote: RemoteIdentity,
    ) -> RepositoryRecord:
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
