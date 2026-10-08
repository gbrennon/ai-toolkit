from pathlib import Path

from ai_toolkit.agent_registry.instruction_resolver import InstructionResolver
from ai_toolkit.agent_registry.instruction_targets import GlobalInstructionTargets
from ai_toolkit.agent_registry.models import InstructionSourceKind


def _resolver(tmp_path: Path, global_path: Path) -> InstructionResolver:
    manifest = tmp_path / "agent_targets.txt"
    manifest.write_text(f"{global_path}\n", encoding="utf-8")
    return InstructionResolver(GlobalInstructionTargets(manifest))


def test_local_instructions_shadow_per_repository_and_global_sources(
    tmp_path: Path,
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

    result = _resolver(tmp_path, global_path).resolve(root, managed)

    assert result.selected is not None
    assert result.selected.kind is InstructionSourceKind.LOCAL
    assert result.selected.path == local.resolve()
    assert [source.kind for source in result.sources] == [
        InstructionSourceKind.LOCAL,
        InstructionSourceKind.PER_REPOSITORY,
        InstructionSourceKind.GLOBAL,
    ]


def test_per_repository_instructions_shadow_global_source_when_local_is_absent(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    managed = tmp_path / "managed" / "AGENT.md"
    managed.parent.mkdir()
    managed.write_text("managed-only", encoding="utf-8")
    global_path = tmp_path / "global" / "AGENTS.md"
    global_path.parent.mkdir()
    global_path.write_text("global-only", encoding="utf-8")

    result = _resolver(tmp_path, global_path).resolve(root, managed)

    assert result.selected is not None
    assert result.selected.kind is InstructionSourceKind.PER_REPOSITORY
    assert result.selected.path == managed.resolve()


def test_global_source_is_selected_when_local_and_managed_files_are_absent(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    managed = tmp_path / "managed" / "AGENT.md"
    global_path = tmp_path / "global" / "AGENTS.md"
    global_path.parent.mkdir()
    global_path.write_text("global-only", encoding="utf-8")

    result = _resolver(tmp_path, global_path).resolve(root, managed)

    assert result.selected is not None
    assert result.selected.kind is InstructionSourceKind.GLOBAL
    assert result.selected.path == global_path.resolve()


def test_resolution_has_no_selected_source_when_all_candidates_are_absent(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    managed = tmp_path / "managed" / "AGENT.md"
    global_path = tmp_path / "global" / "AGENTS.md"

    result = _resolver(tmp_path, global_path).resolve(root, managed)

    assert result.selected is None
    assert not any(source.exists for source in result.sources)


def test_manifest_targets_are_read_only_and_deduplicated(tmp_path: Path) -> None:
    first = tmp_path / "first" / "AGENTS.md"
    second = tmp_path / "second" / "AGENTS.md"
    manifest = tmp_path / "agent_targets.txt"
    manifest.write_text(
        f"# configured target\n{first}\n{first}\n{second}\n", encoding="utf-8"
    )
    before = manifest.read_bytes()

    candidates = GlobalInstructionTargets(manifest).candidates()

    assert candidates == (first.resolve(), second.resolve())
    assert manifest.read_bytes() == before
