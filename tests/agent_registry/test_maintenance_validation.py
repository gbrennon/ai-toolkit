from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from ai_toolkit.agent_registry.editor_port import EditorPort
from ai_toolkit.agent_registry.errors import InvalidOperationError
from ai_toolkit.agent_registry.git_port import GitPort
from ai_toolkit.agent_registry.models import RepositoryRecord
from ai_toolkit.agent_registry.paths import RegistryPaths
from ai_toolkit.agent_registry.service import RegistryService
from ai_toolkit.agent_registry.query_service import RegistryQueryService


INSTANT = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _agent(repository_id: str, remote: str) -> str:
    return "\n".join(
        [
            "---",
            "registrySchema: 1",
            f"repositoryId: {repository_id}",
            f"gitRemote: {remote}",
            "configVersion: 1",
            "lastReviewed: 2026-01-01T00:00:00Z",
            "---",
            "# AGENT.md",
            "",
            "## Scope",
            "Global policy.",
            "",
            "## Precedence",
            "Registry policy.",
            "",
            "## Repository identity",
            "Identity.",
            "",
            "## Required behavior",
            "Behavior.",
            "",
            "## Architecture and coding standards",
            "Standards.",
            "",
            "## Verification",
            "Verification.",
            "",
            "## Skills",
            "- No global skills selected.",
            "",
            "## Hooks",
            "- No global hooks selected.",
            "",
            "## Security and secrets",
            "No secrets.",
            "",
            "## Change policy",
            "Registry changes only.",
            "",
        ]
    )


def _prepared(
    tmp_path: Path,
    specifications: tuple[tuple[str, str], ...] = (
        ("beta", "https://example.test/acme/beta"),
        ("alpha", "https://example.test/acme/alpha"),
    ),
) -> tuple[RegistryPaths, RegistryQueryService, tuple[RepositoryRecord, ...]]:
    paths = RegistryPaths(tmp_path / "registry")
    current_root = [tmp_path]
    current_remote = [""]

    def resolve_worktree_root(_path: Path) -> Path:
        return current_root[0]

    def canonical_remote(_path: Path) -> str:
        return "origin"

    def remote_url(_path: Path, _remote: str = "origin") -> str:
        return current_remote[0]

    git = cast(
        GitPort,
        SimpleNamespace(
            resolve_worktree_root=resolve_worktree_root,
            canonical_remote=canonical_remote,
            remote_url=remote_url,
        ),
    )

    def edit(content: str) -> str:
        return content

    editor = cast(EditorPort, SimpleNamespace(edit=edit))
    service = RegistryService(paths, git=git, editor=editor, clock=lambda: INSTANT)
    service.initialize()
    records: list[RepositoryRecord] = []
    for repository_id, remote in specifications:
        repository = tmp_path / repository_id
        repository.mkdir()
        repository.joinpath("AGENT.md").write_text(
            _agent(repository_id, remote), encoding="utf-8"
        )
        current_root[0] = repository.resolve()
        current_remote[0] = remote
        records.append(service.register(repository, review=False))
    return paths, RegistryQueryService(paths, git=cast(GitPort, git)), tuple(records)


def test_validate_reports_a_valid_registry_without_local_repository_access(
    tmp_path: Path,
) -> None:
    paths, service, records = _prepared(tmp_path)

    for record in records:
        record.local_path.joinpath("AGENT.md").unlink()
        record.local_path.joinpath("agent_rules").mkdir()

    report = service.validate()

    assert report.is_valid
    assert paths.registry_file.is_file()


def test_validate_aggregates_root_record_and_artifact_issues(tmp_path: Path) -> None:
    paths, service, records = _prepared(tmp_path, (("alpha", "https://example.test/acme/alpha"),))
    repository = paths.repository(records[0].repository_id)
    repository.agent_config.write_text("not an AGENT document", encoding="utf-8")
    repository.metadata.write_text("{}", encoding="utf-8")
    repository.skills.write_text("{}", encoding="utf-8")
    repository.hooks.write_text("{}", encoding="utf-8")
    repository.changes_audit.write_text("{bad}\n", encoding="utf-8")

    payload = json.loads(paths.registry_file.read_text(encoding="utf-8"))
    payload["unexpectedRoot"] = True
    payload["repositories"].append({"id": "broken"})
    paths.registry_file.write_text(json.dumps(payload), encoding="utf-8")

    report = service.validate()

    fields = {issue.field for issue in report.issues}
    codes = {issue.code for issue in report.issues}
    assert any(field.startswith("root.unexpectedRoot") for field in fields)
    assert any(field.startswith("repositories[1].") for field in fields)
    assert {"digest", "markdown", "metadata", "skills", "hooks"} <= codes
    assert "malformed-audit-event" in codes


def test_validate_reports_missing_managed_artifacts(tmp_path: Path) -> None:
    paths, service, records = _prepared(tmp_path, (("alpha", "https://example.test/acme/alpha"),))
    repository = paths.repository(records[0].repository_id)
    repository.agent_config.unlink()
    repository.metadata.unlink()
    repository.skills.unlink()
    repository.hooks.unlink()
    repository.changes_audit.unlink()

    report = service.validate()

    missing = [issue for issue in report.issues if issue.code == "missing"]
    assert {issue.field for issue in missing} == {
        str(repository.agent_config),
        str(repository.metadata),
        str(repository.skills),
        str(repository.hooks),
        str(repository.changes_audit),
    }


def test_validate_can_select_one_repository_record(tmp_path: Path) -> None:
    paths, service, records = _prepared(tmp_path)
    for record in records:
        paths.repository(record.repository_id).agent_config.write_text(
            "not an AGENT document", encoding="utf-8"
        )

    report = service.validate("alpha")

    assert report.issues
    assert all(
        str(paths.repository("beta").agent_config) not in issue.field
        for issue in report.issues
    )

def test_list_repositories_filters_active_records_and_sorts_by_id(
    tmp_path: Path,
) -> None:
    paths, service, _ = _prepared(tmp_path)
    payload = json.loads(paths.registry_file.read_text(encoding="utf-8"))
    payload["repositories"] = list(reversed(payload["repositories"]))
    payload["repositories"][0]["status"] = "archived"
    paths.registry_file.write_text(json.dumps(payload), encoding="utf-8")

    active = service.list_repositories()
    all_records = service.list_repositories(include_inactive=True)

    assert tuple(record.repository_id for record in active) == ("alpha",)
    assert tuple(record.repository_id for record in all_records) == ("alpha", "beta")
    assert all_records[1].status.value == "archived"


@pytest.mark.parametrize("registry_state", ["missing", "corrupt"])
def test_list_repositories_raises_typed_error_for_unreadable_registry(
    tmp_path: Path, registry_state: str
) -> None:
    paths = RegistryPaths(tmp_path / "registry")
    if registry_state == "corrupt":
        paths.root.mkdir()
        paths.registry_file.write_text("{bad", encoding="utf-8")
    service = RegistryQueryService(RegistryPaths(tmp_path / "registry"))

    with pytest.raises(InvalidOperationError):
        service.list_repositories()
