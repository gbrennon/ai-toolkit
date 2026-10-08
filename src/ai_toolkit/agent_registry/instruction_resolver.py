from dataclasses import dataclass, field
from pathlib import Path

from .instruction_targets import GlobalInstructionTargets
from .models import (
    InstructionResolution,
    InstructionSource,
    InstructionSourceKind,
)


@dataclass(frozen=True, slots=True)
class InstructionResolver:
    """Resolve local, per-repository, and global instruction paths by precedence."""

    targets: GlobalInstructionTargets = field(default_factory=GlobalInstructionTargets)

    def resolve(
        self,
        worktree_root: Path,
        managed_path: Path | None,
    ) -> InstructionResolution:
        """Select the first existing instruction file without loading file content."""
        candidates = [
            self._source(InstructionSourceKind.LOCAL, worktree_root / "AGENT.md")
        ]
        if managed_path is not None:
            candidates.append(
                self._source(InstructionSourceKind.PER_REPOSITORY, managed_path)
            )
        candidates.extend(
            self._source(InstructionSourceKind.GLOBAL, path)
            for path in self.targets.candidates()
        )
        ordered = tuple(candidates)
        selected = next((source for source in ordered if source.exists), None)
        return InstructionResolution(ordered, selected)

    def _source(self, kind: InstructionSourceKind, path: Path) -> InstructionSource:
        resolved = path.expanduser().resolve()
        return InstructionSource(kind, resolved, resolved.is_file())
