from pathlib import Path

from .discovery import DiscoveryService
from .errors import InvalidOperationError, RegistryError
from .git import GitResolver
from .git_port import GitPort
from .json_document_store import JsonDocumentStore
from .maintenance import validate_registry
from .models import (
    AuditReadReport,
    DiscoveryResult,
    RegistryDocument,
    RepositoryRecord,
    RepositoryStatus,
    ValidationReport,
)
from .paths import RegistryPaths
from .service_maintenance import audit_selection, read_audit, root_health
from .validation import parse_registry_document


class RegistryQueryService:
    """Read and validate global registry state without mutating it."""

    def __init__(
        self,
        paths: RegistryPaths,
        git: GitPort | None = None,
        store: JsonDocumentStore | None = None,
    ) -> None:
        self._paths = paths
        self._git = GitResolver() if git is None else git
        self._store = JsonDocumentStore() if store is None else store

    def discover(self, repository_path: Path | str) -> DiscoveryResult:
        """Resolve and validate one repository through the discovery service."""
        return DiscoveryService(self._paths, git=self._git, store=self._store).discover(
            repository_path
        )

    def audit(self, repository_id: str | None = None) -> AuditReadReport:
        """Read global audit events in deterministic repository and append order."""
        registry = self._load_registry()
        records = audit_selection(registry, repository_id)
        return read_audit(self._paths, records, repository_id)

    def doctor(self) -> ValidationReport:
        """Report global registry health without reading repositories or mutating state."""
        return ValidationReport(root_health(self._paths, self._store))

    def validate(self, repository_id: str | None = None) -> ValidationReport:
        """Return registry and managed artifact validation issues."""
        return validate_registry(self._paths, self._store, repository_id)

    def list_repositories(
        self, include_inactive: bool = False
    ) -> tuple[RepositoryRecord, ...]:
        """Return repository records in deterministic identifier order."""
        registry = self._load_registry()
        records = (
            record
            for record in registry.repositories
            if include_inactive or record.status is RepositoryStatus.ACTIVE
        )
        return tuple(sorted(records, key=lambda record: record.repository_id))

    def _load_registry(self) -> RegistryDocument:
        try:
            return parse_registry_document(
                self._store.read(self._paths.registry_file), self._paths
            )
        except (OSError, RegistryError) as error:
            raise InvalidOperationError(
                f"registry is not initialized or valid: {self._paths.registry_file}"
            ) from error
