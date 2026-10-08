import os
import stat
from pathlib import Path

import pytest

from ai_toolkit.agent_registry.errors import AtomicWriteError, MalformedDocumentError
from ai_toolkit.agent_registry.storage import AtomicWriter, JsonDocumentStore, NdjsonEventStore


def test_atomic_writer_replaces_bytes_and_applies_permissions(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "config.bin"
    writer = AtomicWriter()

    writer.write_bytes(path, b"first")
    writer.write_bytes(path, b"second")

    assert path.read_bytes() == b"second"
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700


def test_atomic_writer_writes_utf8_text(tmp_path: Path) -> None:
    path = tmp_path / "config.txt"

    AtomicWriter().write_text(path, "café")

    assert path.read_text(encoding="utf-8") == "café"


def test_atomic_writer_cleans_temporary_file_after_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.bin"
    writer = AtomicWriter()

    def fail_replace(source: str, target: str) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(AtomicWriteError):
        writer.write_bytes(path, b"data")

    assert not list(tmp_path.glob(".*.tmp"))
    assert not path.exists()


def test_json_document_store_round_trips_utf8_document(tmp_path: Path) -> None:
    path = tmp_path / "document.json"
    document = {"name": "café", "items": [1, 2]}
    store = JsonDocumentStore()

    store.write(path, document)

    assert store.read(path) == document


def test_json_document_store_reports_malformed_path(tmp_path: Path) -> None:
    path = tmp_path / "document.json"
    path.write_text("{bad", encoding="utf-8")

    with pytest.raises(MalformedDocumentError) as error:
        JsonDocumentStore().read(path)

    assert str(path) in str(error.value)


def test_ndjson_event_store_preserves_append_order(tmp_path: Path) -> None:
    path = tmp_path / "events.ndjson"
    store = NdjsonEventStore()

    store.append(path, {"sequence": 1})
    store.append(path, {"sequence": 2})

    assert store.read(path) == [{"sequence": 1}, {"sequence": 2}]


def test_ndjson_event_store_reports_malformed_line_number(tmp_path: Path) -> None:
    path = tmp_path / "events.ndjson"
    path.write_text('{"sequence": 1}\n{bad}\n', encoding="utf-8")

    with pytest.raises(MalformedDocumentError) as error:
        NdjsonEventStore().read(path)

    assert "line 2" in str(error.value)
    assert str(path) in str(error.value)
