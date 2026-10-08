from collections.abc import Callable
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile

from .editor import RegistryEditor
from .editor_port import EditorPort
from .errors import InvalidOperationError, RegistryError
from .git import GitResolver
from .git_port import GitPort
from .hashing import Sha256Digest
from .identity import RemoteIdentity, choose_repository_id, normalize_remote
from .markdown import validate_agent_markdown
from .models import (
    AuditReadReport,
    RegistryDocument,
    RepositoryRecord,
    RepositoryStatus,
    ValidationReport,
)
from .paths import RegistryPaths
from .service_helpers import (
    manifest_text,
    publish_repository,
    raise_incompatible,
    read_agent,
    remove_published,
    same_identity,
    stage_repository,
    validate_collisions,
    validate_existing,
)
from .storage import AtomicWriter, JsonDocumentStore
from .service_maintenance import audit_selection, read_audit, root_health
from .validation import parse_registry_document

Clock = Callable[[], datetime]

_INITIAL_README = "# Agent Registry\n\nThis directory is the global agent registry.\n"
_INITIAL_CHANGELOG = "# Changelog\n\n- Registry initialized.\n"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("registry clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _empty_registry(instant: datetime) -> RegistryDocument:
    return RegistryDocument(1, "1", instant, ())


def _ensure_directory(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise_incompatible(path, "required directory is not a directory")
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.chmod(0o700)


def _ensure_empty_directory(path: Path) -> None:
    if any(path.iterdir()):
        raise_incompatible(path, "repository artifacts already exist")


def _write_initial_file(path: Path, content: str) -> None:
    if path.exists():
        try:
            compatible = path.is_file() and path.read_text(encoding="utf-8") == content
        except OSError, UnicodeDecodeError:
            compatible = False
        if not compatible:
            raise_incompatible(path, "existing content is incompatible")
        return
    AtomicWriter().write_text(path, content)


def _validate_content(content: str, record: RepositoryRecord) -> None:
    report = validate_agent_markdown(content, record)
    if not report.is_valid:
        details = "; ".join(
            f"{issue.field}: {issue.message}" for issue in report.issues
        )
        raise InvalidOperationError(f"AGENT.md is invalid: {details}")


class RegistryService:
    """Initialize and register repositories in the global agent registry."""

    def __init__(
        self,
        paths: RegistryPaths,
        git: GitPort | None = None,
        editor: EditorPort | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._paths = paths
        self._git = GitResolver() if git is None else git
        self._editor = RegistryEditor() if editor is None else editor
        self._clock = _now if clock is None else clock
        self._store = JsonDocumentStore()

    def initialize(self) -> None:
        """Create the complete empty registry tree using safe atomic writes."""
        _ensure_directory(self._paths.root)
        allowed = {
            "REGISTRY.json",
            "README.md",
            "CHANGELOG.md",
            "skills",
            "hooks",
            "repos",
        }
        unknown = [
            entry for entry in self._paths.root.iterdir() if entry.name not in allowed
        ]
        if unknown:
            raise_incompatible(
                self._paths.root, f"unexpected existing entry: {unknown[0].name}"
            )
        _ensure_directory(self._paths.skills_dir)
        _ensure_directory(self._paths.hooks_dir)
        _ensure_directory(self._paths.repos_dir)
        _ensure_empty_directory(self._paths.repos_dir)
        self._initialize_registry()
        _write_initial_file(self._paths.readme, _INITIAL_README)
        _write_initial_file(self._paths.changelog, _INITIAL_CHANGELOG)
        _write_initial_file(self._paths.skills_dir / "manifest.json", manifest_text())
        _write_initial_file(self._paths.hooks_dir / "manifest.json", manifest_text())

    def register(self, repository_path: Path, review: bool = True) -> RepositoryRecord:
        """Register one Git worktree from its root AGENT.md without running hooks."""
        root, remote, registry, candidate_id, existing = self._resolve_registration(
            repository_path
        )
        if existing is not None and same_identity(existing, remote, root, candidate_id):
            validate_existing(existing, self._paths)
            return existing
        validate_collisions(registry.repositories, candidate_id, remote, root)
        source = read_agent(root)
        content = self._editor.edit(source) if review else source
        instant = _utc(self._clock())
        record = RepositoryRecord(
            candidate_id,
            remote.canonical_url,
            root,
            self._paths.repository(candidate_id).agent_config,
            Sha256Digest.digest_bytes(content.encode("utf-8")),
            RepositoryStatus.ACTIVE,
            instant,
            instant,
        )
        _validate_content(content, record)
        self._publish_record(registry, record, content)
        return record

    def audit(self, repository_id: str | None = None) -> AuditReadReport:
        """Read global audit events in deterministic repository and append order."""
        registry = self._load_registry()
        records = audit_selection(registry, repository_id)
        return read_audit(self._paths, records, repository_id)

    def doctor(self) -> ValidationReport:
        """Report global registry health without reading repositories or mutating state."""
        return ValidationReport(root_health(self._paths, self._store))

    def _resolve_registration(
        self, repository_path: Path
    ) -> tuple[Path, RemoteIdentity, RegistryDocument, str, RepositoryRecord | None]:
        root = self._git.resolve_worktree_root(repository_path).resolve()
        self._git.canonical_remote(root)
        remote = normalize_remote(self._git.remote_url(root, "origin"))
        registry = self._load_registry()
        candidate_id = choose_repository_id(
            remote, ((record.id, record.git_remote) for record in registry.repositories)
        )
        existing = next(
            (record for record in registry.repositories if record.id == candidate_id),
            None,
        )
        return root, remote, registry, candidate_id, existing

    def _initialize_registry(self) -> None:
        if self._paths.registry_file.exists():
            try:
                document = parse_registry_document(
                    self._store.read(self._paths.registry_file), self._paths
                )
            except (OSError, RegistryError) as error:
                raise_incompatible(self._paths.registry_file, str(error))
            if document.repositories:
                raise_incompatible(
                    self._paths.registry_file, "registry already contains repositories"
                )
            return
        self._store.write(
            self._paths.registry_file, _empty_registry(_utc(self._clock())).to_json()
        )

    def _load_registry(self) -> RegistryDocument:
        try:
            return parse_registry_document(
                self._store.read(self._paths.registry_file), self._paths
            )
        except (OSError, RegistryError) as error:
            raise InvalidOperationError(
                f"registry is not initialized or valid: {self._paths.registry_file}"
            ) from error

    def _publish_record(
        self, registry: RegistryDocument, record: RepositoryRecord, content: str
    ) -> None:
        updated = RegistryDocument(
            registry.schema_version,
            registry.registry_version,
            _utc(self._clock()),
            tuple(
                sorted(
                    (*registry.repositories, record),
                    key=lambda item: item.repository_id,
                )
            ),
        )
        with tempfile.TemporaryDirectory(
            prefix=".agent-registry-stage-", dir=self._paths.root
        ) as temporary:
            staged = stage_repository(Path(temporary), record, content)
            destination = self._paths.repository(record.repository_id).directory
            published = False
            try:
                publish_repository(staged, destination)
                published = True
                self._store.write(self._paths.registry_file, updated.to_json())
            except Exception:
                if published:
                    remove_published(destination)
                raise
