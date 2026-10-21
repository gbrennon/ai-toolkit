from pathlib import Path

from .discovery import DiscoveryService
from .git import GitResolver
from .git_port import GitPort
from .instruction_resolver import InstructionResolver
from .json_document_store import JsonDocumentStore
from .models import DiscoveryResult
from .paths import RegistryPaths


class RegistryQueryService:
    """Read and resolve global registry state without mutating it."""

    def __init__(
        self,
        paths: RegistryPaths,
        git: GitPort | None = None,
        store: JsonDocumentStore | None = None,
        resolver: InstructionResolver | None = None,
    ) -> None:
        self._paths = paths
        self._git = GitResolver() if git is None else git
        self._store = JsonDocumentStore() if store is None else store
        self._resolver = InstructionResolver() if resolver is None else resolver

    def discover(self, repository_path: Path | str) -> DiscoveryResult:
        """Resolve and validate one repository through the discovery service."""
        return DiscoveryService(
            self._paths,
            git=self._git,
            store=self._store,
            resolver=self._resolver,
        ).discover(repository_path)
