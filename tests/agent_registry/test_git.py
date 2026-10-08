from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
import subprocess
from typing import cast

import pytest

from ai_toolkit.agent_registry.errors import GitResolutionError, MissingOriginError
from ai_toolkit.agent_registry.git import GitResolver
from ai_toolkit.agent_registry.git_invocation import GitInvocation
from ai_toolkit.agent_registry.git_result import GitResult
from ai_toolkit.agent_registry.git_runner import GitRunner


class TestFakeRunner:
    def __init__(self, responses: Mapping[tuple[str, ...], object]) -> None:
        self.responses = responses
        self.calls: list[GitInvocation] = []

    def __call__(self, invocation: GitInvocation) -> GitResult:
        self.calls.append(invocation)
        return cast(GitResult, self.responses[tuple(invocation.args)])


def test_resolve_worktree_root_uses_git_absolute_result_and_nested_cwd(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    nested = root / "src" / "package"
    nested.mkdir(parents=True)
    runner = TestFakeRunner(
        {
            ("rev-parse", "--show-toplevel"): SimpleNamespace(
                returncode=0,
                stdout=f"{root}\n",
                stderr="",
            )
        }
    )

    resolved = GitResolver(runner).resolve_worktree_root(nested)

    assert resolved == root.resolve()
    invocation = runner.calls[0]
    assert list(invocation.args) == ["rev-parse", "--show-toplevel"]
    assert invocation.cwd == nested.resolve()
    assert invocation.shell is False


def test_git_operations_report_actionable_command_failure(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    runner = TestFakeRunner(
        {
            ("rev-parse", "--show-toplevel"): SimpleNamespace(
                returncode=128,
                stdout="",
                stderr="not a git repository",
            )
        }
    )

    with pytest.raises(GitResolutionError, match="rev-parse.*not a git repository"):
        GitResolver(runner).resolve_worktree_root(repository)


def test_git_executable_failure_is_wrapped_as_resolution_error(tmp_path: Path) -> None:
    def fail_runner(invocation: GitInvocation) -> GitResult:
        raise FileNotFoundError("git executable missing")

    with pytest.raises(GitResolutionError, match="git executable missing"):
        GitResolver(cast(GitRunner, fail_runner)).resolve_worktree_root(tmp_path)


def test_canonical_remote_is_fixed_to_origin_and_resolves_its_url(
    tmp_path: Path,
) -> None:
    runner = TestFakeRunner(
        {
            ("remote", "get-url", "origin"): SimpleNamespace(
                returncode=0,
                stdout="git@github.com:owner/repository.git\n",
                stderr="",
            )
        }
    )

    resolver = GitResolver(runner)

    assert resolver.canonical_remote(tmp_path) == "origin"
    assert resolver.remote_url(tmp_path) == "git@github.com:owner/repository.git"
    assert [list(call.args) for call in runner.calls] == [
        ["remote", "get-url", "origin"],
        ["remote", "get-url", "origin"],
    ]


def test_missing_origin_is_typed_and_does_not_fall_back_to_another_remote(
    tmp_path: Path,
) -> None:
    runner = TestFakeRunner(
        {
            ("remote", "get-url", "origin"): SimpleNamespace(
                returncode=2,
                stdout="",
                stderr="No such remote 'origin'",
            )
        }
    )

    with pytest.raises(MissingOriginError, match="origin"):
        GitResolver(runner).canonical_remote(tmp_path)

    assert len(runner.calls) == 1
    assert list(runner.calls[0].args) == ["remote", "get-url", "origin"]


def test_remote_lookup_is_shell_free_and_uses_injected_runner(tmp_path: Path) -> None:
    runner = TestFakeRunner(
        {
            ("remote", "get-url", "origin"): SimpleNamespace(
                returncode=0,
                stdout="https://example.test/owner/repository\n",
                stderr="",
            )
        }
    )

    GitResolver(runner).remote_url(tmp_path)

    invocation = runner.calls[0]
    assert invocation.shell is False
    assert invocation.check is False
    assert invocation.capture_output is True
    assert invocation.text is True


def test_real_git_root_resolution_from_nested_directory_is_normalized(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    nested = repository / "deep" / "path"
    nested.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.test/owner/repository.git"],
        cwd=repository,
        check=True,
    )

    resolver = GitResolver()

    assert resolver.resolve_worktree_root(nested) == repository.resolve()
    assert resolver.canonical_remote(nested) == "origin"
    assert resolver.remote_url(nested) == "https://example.test/owner/repository.git"


def test_git_resolution_does_not_modify_repository_files(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    nested = repository / "nested"
    nested.mkdir(parents=True)
    (repository / "tracked.txt").write_bytes(b"stable")
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.test/owner/repository.git"],
        cwd=repository,
        check=True,
    )
    before = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }

    resolver = GitResolver()
    resolver.resolve_worktree_root(nested)
    resolver.canonical_remote(nested)
    resolver.remote_url(nested)

    after = {
        path.relative_to(repository): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file()
    }
    assert after == before
