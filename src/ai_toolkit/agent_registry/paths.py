import re
from dataclasses import dataclass, field
from pathlib import Path

from .errors import PathEscapeError
from .path_containment import PathContainment
from .repository_paths import RepositoryPaths

_REPOSITORY_ID = re.compile(r"[a-z0-9][a-z0-9._-]*")


@dataclass(frozen=True, slots=True)
class RegistryPaths:
    root: Path = field(default_factory=lambda: Path.home() / ".agent-registry")

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.expanduser().resolve())

    @property
    def registry_file(self) -> Path:
        return self.root / "REGISTRY.json"

    @property
    def readme(self) -> Path:
        return self.root / "README.md"

    @property
    def changelog(self) -> Path:
        return self.root / "CHANGELOG.md"

    @property
    def skills_dir(self) -> Path:
        return self.root / "skills"

    @property
    def hooks_dir(self) -> Path:
        return self.root / "hooks"

    @property
    def repos_dir(self) -> Path:
        return self.root / "repos"

    def repository(self, repo_id: str) -> RepositoryPaths:
        if not isinstance(repo_id, str) or _REPOSITORY_ID.fullmatch(repo_id) is None:
            raise PathEscapeError(f"unsafe repository id: {repo_id!r}")
        directory = PathContainment(self.repos_dir).resolve(repo_id)
        return RepositoryPaths(directory)
