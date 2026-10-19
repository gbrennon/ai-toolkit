from dataclasses import dataclass
from pathlib import Path

from .artifact_validator import RegistryArtifactValidator
from .errors import InvalidOperationError, MissingOriginError
from .git import GitResolver
from .git_port import GitPort
from .identity import RemoteIdentity, normalize_remote
from .instruction_resolver import InstructionResolver
from .json_document_store import JsonDocumentStore
from .models import DiscoveryResult, InstructionResolution, RegistryDocument
from .paths import RegistryPaths
from .record_selector import RegistryRecordSelector
from .validation import parse_registry_document


@dataclass(frozen=True, slots=True, init=False)
class DiscoveryService:
    """Resolve and validate global agent configuration for one Git worktree."""

    _paths: RegistryPaths
    _git: GitPort
    _resolver: InstructionResolver
    _store: JsonDocumentStore
    _selector: RegistryRecordSelector
    _validator: RegistryArtifactValidator

    def __init__(
        self,
        paths: RegistryPaths,
        git: GitPort | None = None,
        store: JsonDocumentStore | None = None,
        resolver: InstructionResolver | None = None,
    ) -> None:
        selected_store = JsonDocumentStore() if store is None else store
        object.__setattr__(self, "_paths", paths)
        object.__setattr__(self, "_git", GitResolver() if git is None else git)
        object.__setattr__(self, "_store", selected_store)
        object.__setattr__(
            self,
            "_resolver",
            InstructionResolver() if resolver is None else resolver,
        )
        object.__setattr__(self, "_selector", RegistryRecordSelector())
        object.__setattr__(
            self,
            "_validator",
            RegistryArtifactValidator(paths, selected_store),
        )

    def discover(self, repository_path: Path | str) -> DiscoveryResult:
        """Resolve one worktree and validate only its global registry artifacts."""
        root = self._git.resolve_worktree_root(Path(repository_path)).resolve()
        remote = self._resolve_origin(root)
        registry = self._load_registry()
        record = self._selector.select(registry, root, remote)
        report = self._validator.validate(record, registry.schema_version)
        instruction_resolution = self._resolver.resolve(
            root, record.agent_config_path
        )
        return DiscoveryResult(
            record.repository_id,
            record.agent_config_path,
            report,
            instruction_resolution,
        )

    def resolve_instructions(
        self, repository_path: Path | str
    ) -> InstructionResolution:
        """Resolve effective instruction paths even without a registry mapping."""
        root = self._git.resolve_worktree_root(Path(repository_path)).resolve()
        managed_path = self._managed_path_or_none(root)
        return self._resolver.resolve(root, managed_path)

    def _managed_path_or_none(self, root: Path) -> Path | None:
        try:
            registry = self._load_registry()
            remote = self._resolve_origin(root)
            record = self._selector.select(registry, root, remote)
        except InvalidOperationError as error:
            if self._is_unregistered(error):
                return None
            raise
        return record.agent_config_path

    def _is_unregistered(self, error: InvalidOperationError) -> bool:
        message = str(error)
        return message.startswith(
            (
                "registry is not initialized",
                "no active registry mapping",
            )
        )

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
