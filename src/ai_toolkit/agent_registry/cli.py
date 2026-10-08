from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import sys
from pathlib import Path
from typing import cast

from .errors import RegistryError
from .paths import RegistryPaths
from .service import RegistryService

CommandHandler = Callable[[RegistryService, argparse.Namespace], int]


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

    audit = commands.add_parser("audit", help="read registry audit events")
    audit.add_argument("repository_id", nargs="?")
    commands.add_parser("doctor", help="check registry health")

    migrate = commands.add_parser("migrate", help="migrate registry metadata")
    migrate.add_argument("repository_id")
    migrate.add_argument("--remote")
    migrate.add_argument("--local-path", type=Path)
    return parser


def _build_service(registry_root: Path | None) -> RegistryService:
    paths = RegistryPaths() if registry_root is None else RegistryPaths(registry_root)
    return RegistryService(paths)


def _initialize(service: RegistryService, _arguments: argparse.Namespace) -> int:
    service.initialize()
    print("Initialized agent registry.")
    return 0


def _register(service: RegistryService, arguments: argparse.Namespace) -> int:
    path = cast(Path, arguments.path)
    review = not cast(bool, arguments.no_review)
    record = service.register(path, review=review)
    print(f"Registered {record.id} ({record.git_remote}).")
    print(f"Managed configuration: {record.agent_config_path}")
    return 0


def _audit(service: RegistryService, arguments: argparse.Namespace) -> int:
    repository_id = cast(str | None, arguments.repository_id)
    report = service.audit(repository_id)
    print(f"Audit events: {len(report.events)}")
    for event in report.events:
        print(f"{event.repository_id}: {event.operation} ({event.outcome})")
    for issue in report.issues:
        print(f"Audit issue: {issue.field}: {issue.message}")
    return 1 if report.issues else 0


def _doctor(service: RegistryService, _arguments: argparse.Namespace) -> int:
    report = service.doctor()
    if report.is_valid:
        print("Registry doctor: healthy.")
        return 0
    print(f"Registry doctor: {len(report.issues)} issue(s).")
    for issue in report.issues:
        print(f"{issue.field}: {issue.message}")
    return 1


def _migrate(service: RegistryService, arguments: argparse.Namespace) -> int:
    repository_id = cast(str, arguments.repository_id)
    remote = cast(str | None, arguments.remote)
    local_path = cast(Path | None, arguments.local_path)
    record = service.migrate(repository_id, git_remote=remote, local_path=local_path)
    print(f"Migrated {record.id} ({record.git_remote}).")
    print(f"Local path: {record.local_path}")
    return 0


def _dispatch(service: RegistryService, arguments: argparse.Namespace) -> int:
    handlers: dict[str, CommandHandler] = {
        "initialize": _initialize,
        "register": _register,
        "audit": _audit,
        "doctor": _doctor,
        "migrate": _migrate,
    }
    command = cast(str, arguments.command)
    handler = handlers.get(command)
    if handler is None:
        raise RegistryError(f"unsupported command: {command}")
    return handler(service, arguments)


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
