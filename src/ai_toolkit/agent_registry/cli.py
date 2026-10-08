from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import sys
from pathlib import Path
from typing import cast

from .errors import RegistryError
from .git import GitResolver
from .json_document_store import JsonDocumentStore
from .migration_service import RegistryMigrationService
from .models import ValidationReport
from .paths import RegistryPaths
from .query_service import RegistryQueryService
from .service import RegistryService

@dataclass(frozen=True, slots=True)
class RegistryServices:
    """Typed composition of registry mutation and query modules."""

    registration: RegistryService
    query: RegistryQueryService
    migration: RegistryMigrationService


CommandHandler = Callable[[RegistryServices, argparse.Namespace], int]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the global agent registry")
    parser.add_argument(
        "--registry-root",
        type=Path,
        default=None,
        help="override the global registry directory",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("initialize", help="initialize the global registry")

    register = commands.add_parser("register", help="register a Git repository")
    register.add_argument("path", type=Path)
    register.add_argument(
        "--no-review",
        action="store_true",
        help="register without opening the configured editor",
    )
    discover = commands.add_parser("discover", help="discover a repository configuration")
    discover.add_argument("path", type=Path)

    validate = commands.add_parser("validate", help="validate registry artifacts")
    validate.add_argument("repository_id", nargs="?")

    list_command = commands.add_parser("list", help="list registered repositories")
    list_command.add_argument(
        "--include-inactive",
        action="store_true",
        help="include archived and blocked repositories",
    )


    audit = commands.add_parser("audit", help="read registry audit events")
    audit.add_argument("repository_id", nargs="?")
    commands.add_parser("doctor", help="check registry health")

    migrate = commands.add_parser("migrate", help="migrate registry metadata")
    migrate.add_argument("repository_id")
    migrate.add_argument("--remote")
    migrate.add_argument("--local-path", type=Path)
    return parser


def _build_service(registry_root: Path | None) -> RegistryServices:
    paths = RegistryPaths() if registry_root is None else RegistryPaths(registry_root)
    git = GitResolver()
    store = JsonDocumentStore()
    return RegistryServices(
        RegistryService(paths, git=git),
        RegistryQueryService(paths, git=git, store=store),
        RegistryMigrationService(paths, store=store),
    )


def _initialize(services: RegistryServices, _arguments: argparse.Namespace) -> int:
    services.registration.initialize()
    print("Initialized agent registry.")
    return 0


def _register(services: RegistryServices, arguments: argparse.Namespace) -> int:
    path = cast(Path, arguments.path)
    review = not cast(bool, arguments.no_review)
    record = services.registration.register(path, review=review)
    print(f"Registered {record.id} ({record.git_remote}).")
    print(f"Managed configuration: {record.agent_config_path}")
    return 0

def _report(label: str, report: ValidationReport) -> int:
    if report.is_valid:
        print(f"{label}: healthy.")
        return 0
    print(f"{label} found {len(report.issues)} issue(s).")
    for issue in report.issues:
        print(f"{issue.field}: {issue.message}")
    return 1


def _discover(services: RegistryServices, arguments: argparse.Namespace) -> int:
    path = cast(Path, arguments.path)
    result = services.query.discover(path)
    print(f"Discovered {result.repository_id}.")
    print(f"Managed configuration: {result.agent_config_path}")
    selected = result.instruction_resolution.selected
    if selected is None:
        print("Instructions: none")
    else:
        print(f"Instructions: {selected.kind.value} ({selected.path})")
    return _report("Discovery", result.validation_report)


def _validate(services: RegistryServices, arguments: argparse.Namespace) -> int:
    repository_id = cast(str | None, arguments.repository_id)
    return _report("Registry validation", services.query.validate(repository_id))


def _list(services: RegistryServices, arguments: argparse.Namespace) -> int:
    include_inactive = cast(bool, arguments.include_inactive)
    records = services.query.list_repositories(include_inactive=include_inactive)
    print(f"Repositories: {len(records)}")
    for record in records:
        print(f"{record.repository_id} ({record.status.value})")
    return 0



def _audit(services: RegistryServices, arguments: argparse.Namespace) -> int:
    repository_id = cast(str | None, arguments.repository_id)
    report = services.query.audit(repository_id)
    print(f"Audit events: {len(report.events)}")
    for event in report.events:
        print(f"{event.repository_id}: {event.operation} ({event.outcome})")
    for issue in report.issues:
        print(f"Audit issue: {issue.field}: {issue.message}")
    return 1 if report.issues else 0


def _doctor(services: RegistryServices, _arguments: argparse.Namespace) -> int:
    report = services.query.doctor()
    if report.is_valid:
        print("Registry doctor: healthy.")
        return 0
    print(f"Registry doctor: {len(report.issues)} issue(s).")
    for issue in report.issues:
        print(f"{issue.field}: {issue.message}")
    return 1


def _migrate(services: RegistryServices, arguments: argparse.Namespace) -> int:
    repository_id = cast(str, arguments.repository_id)
    remote = cast(str | None, arguments.remote)
    local_path = cast(Path | None, arguments.local_path)
    record = services.migration.migrate(
        repository_id, git_remote=remote, local_path=local_path
    )
    print(f"Migrated {record.id} ({record.git_remote}).")
    print(f"Local path: {record.local_path}")
    return 0


def _dispatch(services: RegistryServices, arguments: argparse.Namespace) -> int:
    handlers: dict[str, CommandHandler] = {
        "initialize": _initialize,
        "register": _register,
        "discover": _discover,
        "validate": _validate,
        "list": _list,
        "audit": _audit,
        "doctor": _doctor,
        "migrate": _migrate,
    }
    command = cast(str, arguments.command)
    handler = handlers.get(command)
    if handler is None:
        raise RegistryError(f"unsupported command: {command}")
    return handler(services, arguments)


def main(argv: Sequence[str] | None = None) -> int:
    """Run one global agent-registry command and return its process status."""
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 1
    try:
        registry_root = cast(Path | None, arguments.registry_root)
        return _dispatch(_build_service(registry_root), arguments)
    except (RegistryError, OSError, ValueError) as error:
        print(f"agent-registry: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
