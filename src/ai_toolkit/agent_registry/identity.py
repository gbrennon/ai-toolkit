from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
import re
from typing import cast
from urllib.parse import unquote, urlsplit

from .errors import IdentityCollisionError, RemoteNormalizationError

_ID_PART = re.compile(r"[a-z0-9._-]+")
_REMOTE_PART = re.compile(r"^[A-Za-z0-9._~-]+$")
_SCP_REMOTE = re.compile(r"^(?:[^/@:]+@)?([^/:]+):(.+)$")
Record = Mapping[str, str]
ExistingEntry = tuple[str, "RemoteIdentity | str"] | Record
ExistingIdentity = Mapping[str, "RemoteIdentity | str"] | Iterable[ExistingEntry]


@dataclass(frozen=True, slots=True)
class RemoteIdentity:
    host: str
    owner: str
    repository: str
    port: int | None = None

    def __post_init__(self) -> None:
        host = self.host.casefold()
        owner = _normalize_owner(self.owner)
        repository = self.repository.casefold()
        _validate_identity_parts(host, owner, repository)
        object.__setattr__(self, "host", host)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "repository", repository)


    @property
    def normalized(self) -> str:
        authority = self.host if self.port is None else f"{self.host}:{self.port}"
        return f"{authority}/{self.owner}/{self.repository}"

    @property
    def canonical_url(self) -> str:
        return f"https://{self.normalized}"

    @property
    def owner_groups(self) -> tuple[str, ...]:
        return tuple(self.owner.split("/"))


def normalize_remote(remote: str) -> RemoteIdentity:
    _validate_remote_input(remote)
    if "://" in remote:
        host, port, path = _parse_url_remote(remote)
    else:
        host, port, path = _parse_scp_remote(remote)
    owner, repository = _parse_path(path, remote)
    return RemoteIdentity(host, owner, repository, port)



def normalize_repository_id(value: str) -> str:
    _validate_id_input(value)
    lowered = value.casefold().strip()
    chunks = _ID_PART.findall(lowered)
    candidate = "-".join(chunks).strip(".-_")
    _validate_id_candidate(value, candidate)
    return candidate


def choose_repository_id(
    remote: RemoteIdentity | str,
    existing: ExistingIdentity,
) -> str:
    identity = _as_identity(remote)
    occupied = _occupied_identities(existing)
    base = normalize_repository_id(identity.repository)
    current = occupied.get(base)
    if current is None or current == identity:
        return base
    qualified = normalize_repository_id(f"{identity.owner.replace('/', '-')}-{base}")
    if qualified in occupied:
        raise IdentityCollisionError(qualified, "owner-qualified repository ID is already occupied")
    return qualified


def validate_unique_remotes(records: Iterable[Record]) -> None:
    seen: dict[RemoteIdentity, str] = {}
    for record in records:
        record_id = _record_value(record, "id", "repositoryId")
        remote = normalize_remote(_record_value(record, "gitRemote", "remote"))
        previous = seen.get(remote)
        if previous is not None:
            raise IdentityCollisionError(remote.normalized, "normalized remote is already registered")
        seen[remote] = record_id


def validate_unique_local_paths(records: Iterable[Record]) -> None:
    seen: dict[Path, str] = {}
    for record in records:
        if _record_value(record, "status").casefold() != "active":
            continue
        record_id = _record_value(record, "id", "repositoryId")
        local_path = Path(_record_value(record, "localPath")).expanduser().resolve()
        previous = seen.get(local_path)
        if previous is not None:
            raise IdentityCollisionError(str(local_path), "active local path is already registered")
        seen[local_path] = record_id


def validate_uniqueness(records: Iterable[Record]) -> None:
    materialized = tuple(records)
    validate_unique_remotes(materialized)
    validate_unique_local_paths(materialized)


def _validate_remote_input(remote: str) -> None:
    if not isinstance(remote, str) or not remote:
        raise RemoteNormalizationError(str(remote), "remote must be a nonempty URL")
    if remote != remote.strip():
        raise RemoteNormalizationError(remote, "remote must not contain surrounding whitespace")


def _validate_id_input(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RemoteNormalizationError(str(value), "repository ID must be nonempty")


def _validate_id_candidate(value: str, candidate: str) -> None:
    if not candidate or not candidate[0].isalnum() or not candidate.isascii():
        raise RemoteNormalizationError(value, "repository ID cannot be normalized safely")


def _normalize_owner(owner: str) -> str:
    return "/".join(part.casefold() for part in owner.split("/") if part)


def _validate_identity_parts(host: str, owner: str, repository: str) -> None:
    if not host or not owner or not repository:
        raise ValueError("remote identity components must be nonempty")


def _validate_url_parts(
    remote: str,
    scheme: str,
    query: str,
    fragment: str,
) -> None:
    if scheme not in {"https", "ssh"} or query or fragment:
        raise RemoteNormalizationError(
            remote,
            "only HTTPS and SSH URLs without query or fragment are supported",
        )


def _validate_path_parts(parts: list[str], remote: str) -> None:
    if len(parts) < 2:
        raise RemoteNormalizationError(remote, "remote path must contain an owner and repository")
    for part in parts:
        _validate_path_part(part, remote)


def _validate_path_part(part: str, remote: str) -> None:
    if not part or part in {".", ".."}:
        raise RemoteNormalizationError(remote, "remote path must contain an owner and repository")
    if not _REMOTE_PART.fullmatch(part):
        raise RemoteNormalizationError(remote, "remote path contains an unusable component")


def _validate_url_host(host: str | None, remote: str) -> str:
    if not host:
        raise RemoteNormalizationError(remote, "remote authority has no host")
    return host


def _parse_url_remote(remote: str) -> tuple[str, int | None, str]:
    parsed = urlsplit(remote)
    scheme = parsed.scheme.casefold()
    _validate_url_parts(remote, scheme, parsed.query, parsed.fragment)
    try:
        host = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise RemoteNormalizationError(remote, "remote authority has an invalid port") from error
    normalized_host = _validate_url_host(host, remote)
    default_port = 443 if scheme == "https" else 22
    return normalized_host, None if port in {None, default_port} else port, parsed.path


def _parse_scp_remote(remote: str) -> tuple[str, None, str]:
    match = _SCP_REMOTE.fullmatch(remote)
    if match is None:
        raise RemoteNormalizationError(remote, "remote is not a supported HTTPS, SSH, or SCP-style URL")
    return match.group(1), None, match.group(2)


def _parse_path(path: str, remote: str) -> tuple[str, str]:
    decoded = unquote(path)
    while decoded.endswith("/"):
        decoded = decoded[:-1]
    if decoded.startswith("/"):
        decoded = decoded[1:]
    if decoded.endswith(".git"):
        decoded = decoded[:-4]
    parts = decoded.split("/")
    _validate_path_parts(parts, remote)
    owner = "/".join(part.casefold() for part in parts[:-1])
    repository = parts[-1].casefold()
    return owner, repository

def _as_identity(remote: RemoteIdentity | str) -> RemoteIdentity:
    return remote if isinstance(remote, RemoteIdentity) else normalize_remote(remote)


def _occupied_identities(existing: ExistingIdentity) -> dict[str, RemoteIdentity]:
    if isinstance(existing, Mapping):
        items = cast(Mapping[str, RemoteIdentity | str], existing).items()
    else:
        items = _identity_items(cast(Iterable[ExistingEntry], existing))
    occupied: dict[str, RemoteIdentity] = {}
    for repository_id, remote in items:
        normalized_id = normalize_repository_id(repository_id)
        identity = _as_identity(remote)
        occupied[normalized_id] = identity
    return occupied


def _identity_items(
    entries: Iterable[ExistingEntry],
) -> Iterable[tuple[str, RemoteIdentity | str]]:
    for entry in entries:
        if isinstance(entry, Mapping):
            yield (
                _record_value(entry, "id", "repositoryId"),
                _record_value(entry, "gitRemote", "remote"),
            )
        else:
            yield entry


def _record_value(record: Record, *names: str) -> str:
    for name in names:
        value = record.get(name)
        if value is not None:
            return value
    joined = ", ".join(names)
    raise IdentityCollisionError(joined, "record is missing a required identity field")
