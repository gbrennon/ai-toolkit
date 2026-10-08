from pathlib import Path

import pytest

from ai_toolkit.agent_registry.dependencies import (
    load_skills,
    parse_skill_manifest,
    select_skills,
)
from ai_toolkit.agent_registry.errors import SchemaValidationError
from ai_toolkit.agent_registry.models import SkillDefinition
from ai_toolkit.agent_registry.paths import RegistryPaths


def _write_skill(paths: RegistryPaths, skill_id: str, content: str = "# Skill\n") -> None:
    paths.skills_dir.mkdir(parents=True, exist_ok=True)
    (paths.skills_dir / f"{skill_id}.md").write_text(content, encoding="utf-8")


def test_skills_require_strict_shape_and_resolve_global_files(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    _write_skill(paths, "review", "# Review\n")
    manifest = {"schemaVersion": 1, "entries": [{"id": "review", "version": "2"}]}

    references = parse_skill_manifest(manifest)
    definitions = load_skills(references, paths)

    assert definitions == (
        SkillDefinition("review", "2", paths.skills_dir / "review.md", ()),
    )


def test_skills_reject_unknown_duplicate_and_unsafe_entries(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    bad_manifests = [
        {"schemaVersion": 1, "entries": [{"id": "review", "version": "1", "extra": 1}]},
        {
            "schemaVersion": 1,
            "entries": [
                {"id": "review", "version": "1"},
                {"id": "review", "version": "2"},
            ],
        },
        {"schemaVersion": 1, "entries": [{"id": "../repo/AGENT", "version": "1"}]},
        {"schemaVersion": 1, "entries": [{"id": "/tmp/repo", "version": "1"}]},
    ]

    for manifest in bad_manifests:
        with pytest.raises(SchemaValidationError):
            parse_skill_manifest(manifest)

    with pytest.raises(SchemaValidationError):
        load_skills(parse_skill_manifest({"schemaVersion": 1, "entries": [{"id": "missing", "version": "1"}]}), paths)


def test_skill_selection_is_exact_and_always_is_explicit(tmp_path: Path) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    _write_skill(paths, "always")
    _write_skill(paths, "review")
    _write_skill(paths, "untagged")
    references = parse_skill_manifest(
        {
            "schemaVersion": 1,
            "entries": [
                {"id": "always", "version": "1", "triggers": ["always"]},
                {"id": "review", "version": "1", "triggers": ["review"]},
                {"id": "untagged", "version": "1"},
            ],
        }
    )
    definitions = load_skills(references, paths)

    assert [skill.id for skill in select_skills(definitions, ("review",))] == ["always", "review"]
    assert [skill.id for skill in select_skills(definitions, ("pre-review",))] == ["always"]
    assert [skill.id for skill in select_skills(definitions, ())] == ["always"]
