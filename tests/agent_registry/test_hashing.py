from pathlib import Path

from ai_toolkit.agent_registry.hashing import Sha256Digest


def test_digest_bytes_returns_exact_sha256() -> None:
    digest = Sha256Digest.digest_bytes(b"hello")

    assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_digest_file_hashes_exact_file_bytes(tmp_path: Path) -> None:
    path = tmp_path / "config.bin"
    path.write_bytes(b"\x00\xff\n")

    digest = Sha256Digest.digest_file(path)

    assert digest == "712450d3c4a79eea9509e75dc1dacdeff58034df538536cfae2da882bd8a0c50"
