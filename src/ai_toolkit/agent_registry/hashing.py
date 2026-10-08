import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Sha256Digest:
    @staticmethod
    def digest_bytes(value: bytes) -> str:
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def digest_file(path: Path) -> str:
        return Sha256Digest.digest_bytes(path.read_bytes())
