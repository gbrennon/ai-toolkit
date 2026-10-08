from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from .json_document_store import JsonDocumentStore
from .migration import apply_migration
from .models import RepositoryRecord
from .paths import RegistryPaths

Clock = Callable[[], datetime]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RegistryMigrationService:
    """Apply explicit registry-only repository metadata migrations."""

    def __init__(
        self,
        paths: RegistryPaths,
        store: JsonDocumentStore | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._paths = paths
        self._store = JsonDocumentStore() if store is None else store
        self._clock = _now if clock is None else clock

    def migrate(
        self,
        repository_id: str,
        git_remote: str | None = None,
        local_path: Path | None = None,
    ) -> RepositoryRecord:
        """Migrate active global registry identity metadata without local I/O."""
        return apply_migration(
            self._paths,
            self._store,
            (repository_id, git_remote, local_path, self._clock),
        )
