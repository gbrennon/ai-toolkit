from dataclasses import dataclass
from pathlib import Path

_DEFAULT_MANIFEST = Path.home() / ".config" / "ai-toolkit" / "agent_targets.txt"
_DEFAULT_TARGETS = (
    Path("~/.agents/AGENTS.md"),
    Path("~/.config/opencode/AGENTS.md"),
    Path("~/.omp/agent/AGENTS.md"),
    Path("~/.config/antigravity/AGENTS.md"),
    Path("~/.pi/agent/AGENTS.md"),
)


@dataclass(frozen=True, slots=True)
class GlobalInstructionTargets:
    """Read-only access to global instruction target configuration."""

    manifest: Path = _DEFAULT_MANIFEST

    def candidates(self) -> tuple[Path, ...]:
        """Return configured or default global instruction paths in stable order."""
        configured = self._configured_targets()
        candidates = configured if configured else _DEFAULT_TARGETS
        return self._unique_resolved(candidates)

    def _configured_targets(self) -> tuple[Path, ...]:
        manifest = self.manifest.expanduser().resolve()
        if not manifest.is_file():
            return ()
        configured: list[Path] = []
        for raw in manifest.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            configured.append(Path(line).expanduser().resolve())
        return tuple(configured)

    def _unique_resolved(self, paths: tuple[Path, ...]) -> tuple[Path, ...]:
        unique: list[Path] = []
        for path in paths:
            resolved = path.expanduser().resolve()
            if resolved not in unique:
                unique.append(resolved)
        return tuple(unique)
