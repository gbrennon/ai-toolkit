from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from ai_toolkit.agent_registry.instruction_resolver import InstructionResolver
from ai_toolkit.agent_registry.instruction_targets import GlobalInstructionTargets
from ai_toolkit.agent_registry.models import (
    InstructionResolution,
    InstructionSource,
    InstructionSourceKind,
)


class TestInstructionResolver:
    def _resolver(self, tmp_path: Path, global_path: Path) -> InstructionResolver:
        manifest = tmp_path / "agent_targets.txt"
        manifest.write_text(f"{global_path}\n", encoding="utf-8")
        return InstructionResolver(GlobalInstructionTargets(manifest))

    def test_local_instructions_shadow_managed_and_global_sources(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "repository"
        root.mkdir()
        local = root / "AGENT.md"
        managed = tmp_path / "managed" / "AGENT.md"
        global_path = tmp_path / "global" / "AGENTS.md"
        managed.parent.mkdir()
        global_path.parent.mkdir()
        local.write_text("local-only", encoding="utf-8")
        managed.write_text("managed-only", encoding="utf-8")
        global_path.write_text("global-only", encoding="utf-8")

        result = self._resolver(tmp_path, global_path).resolve(root, managed)

        assert result.selected is not None
        assert result.selected.kind is InstructionSourceKind.LOCAL
        assert result.selected.path == local.resolve()
        assert [source.kind for source in result.sources] == [
            InstructionSourceKind.LOCAL,
            InstructionSourceKind.PER_REPOSITORY,
            InstructionSourceKind.GLOBAL,
        ]

    def test_managed_instructions_shadow_global_when_local_is_absent(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "repository"
        root.mkdir()
        managed = tmp_path / "managed" / "AGENT.md"
        global_path = tmp_path / "global" / "AGENTS.md"
        managed.parent.mkdir()
        global_path.parent.mkdir()
        managed.write_text("managed-only", encoding="utf-8")
        global_path.write_text("global-only", encoding="utf-8")

        result = self._resolver(tmp_path, global_path).resolve(root, managed)

        assert result.selected is not None
        assert result.selected.kind is InstructionSourceKind.PER_REPOSITORY
        assert result.selected.path == managed.resolve()

    def test_global_instructions_are_selected_when_higher_layers_are_absent(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "repository"
        root.mkdir()
        managed = tmp_path / "managed" / "AGENT.md"
        global_path = tmp_path / "global" / "AGENTS.md"
        global_path.parent.mkdir()
        global_path.write_text("global-only", encoding="utf-8")

        result = self._resolver(tmp_path, global_path).resolve(root, managed)

        assert result.selected is not None
        assert result.selected.kind is InstructionSourceKind.GLOBAL
        assert result.selected.path == global_path.resolve()

    def test_resolution_has_no_selected_source_when_all_candidates_are_absent(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "repository"
        root.mkdir()
        managed = tmp_path / "managed" / "AGENT.md"
        global_path = tmp_path / "global" / "AGENTS.md"

        result = self._resolver(tmp_path, global_path).resolve(root, managed)

        assert result.selected is None
        assert not any(source.exists for source in result.sources)

    def test_manifest_targets_ignore_comments_blanks_and_duplicates(
        self, tmp_path: Path
    ) -> None:
        first = tmp_path / "first" / "AGENTS.md"
        second = tmp_path / "second" / "AGENTS.md"
        manifest = tmp_path / "agent_targets.txt"
        manifest.write_text(
            f"\n  # configured target\n  {first}  \n{first}\n{second}\n",
            encoding="utf-8",
        )
        before = manifest.read_bytes()

        candidates = GlobalInstructionTargets(manifest).candidates()

        assert candidates == (first.resolve(), second.resolve())
        assert manifest.read_bytes() == before

    def test_missing_or_empty_manifest_uses_legacy_defaults_without_writing(
        self, tmp_path: Path
    ) -> None:
        missing = tmp_path / "missing.txt"
        expected = tuple(
            Path(path).expanduser().resolve()
            for path in (
                "~/.agents/AGENTS.md",
                "~/.config/opencode/AGENTS.md",
                "~/.omp/agent/AGENTS.md",
                "~/.config/antigravity/AGENTS.md",
                "~/.pi/agent/AGENTS.md",
            )
        )

        assert GlobalInstructionTargets(missing).candidates() == expected
        manifest = tmp_path / "empty.txt"
        manifest.write_text("\n # no targets\n", encoding="utf-8")
        before = manifest.read_bytes()

        assert GlobalInstructionTargets(manifest).candidates() == expected
        assert manifest.read_bytes() == before

    def test_instruction_sources_are_frozen_and_require_resolved_absolute_paths(
        self, tmp_path: Path
    ) -> None:
        unresolved = tmp_path / "nested" / ".." / "AGENT.md"
        with pytest.raises(ValueError):
            InstructionSource(InstructionSourceKind.LOCAL, unresolved, False)

        source = InstructionSource(
            InstructionSourceKind.LOCAL, (tmp_path / "AGENT.md").resolve(), False
        )
        with pytest.raises(FrozenInstanceError):
            setattr(source, "exists", True)

    def test_instruction_resolution_rejects_invalid_selection_and_duplicate_paths(
        self, tmp_path: Path
    ) -> None:
        first = InstructionSource(
            InstructionSourceKind.LOCAL, (tmp_path / "local").resolve(), True
        )
        second = InstructionSource(
            InstructionSourceKind.GLOBAL, (tmp_path / "global").resolve(), True
        )

        with pytest.raises(ValueError):
            InstructionResolution((first, first), first)
        with pytest.raises(ValueError):
            InstructionResolution((first, second), second)
        with pytest.raises(ValueError):
            InstructionResolution((first,), second)
