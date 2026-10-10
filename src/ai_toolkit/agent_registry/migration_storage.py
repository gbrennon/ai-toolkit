import os
from pathlib import Path
import shutil
import tempfile

from .errors import InvalidOperationError


def backup_repository(source: Path, registry_root: Path, repository_id: str) -> Path:
    """Copy managed repository files into a deterministic migration backup."""
    destination_parent = registry_root / "backups"
    destination_parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        destination_parent.chmod(0o700)
    destination = destination_parent / repository_id
    with tempfile.TemporaryDirectory(
        prefix=f".{repository_id}-migration-", dir=destination_parent
    ) as temporary:
        staged = Path(temporary) / repository_id
        try:
            shutil.copytree(source, staged)
            if destination.exists():
                shutil.rmtree(destination)
            os.replace(staged, destination)
        except OSError as error:
            raise InvalidOperationError(
                f"could not back up managed repository files: {source}"
            ) from error
    return destination


def restore_repository(backup: Path, destination: Path) -> None:
    """Restore managed repository files from a migration backup."""
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(backup, destination)


def snapshot_file(path: Path) -> tuple[bytes, int] | None:
    """Capture file bytes and mode for rollback."""
    if not path.exists():
        return None
    return path.read_bytes(), path.stat().st_mode


def restore_file(path: Path, snapshot: tuple[bytes, int] | None) -> None:
    """Restore one file snapshot or remove a file that did not exist."""
    if snapshot is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(snapshot[0])
    if os.name != "nt":
        path.chmod(snapshot[1] & 0o777)
