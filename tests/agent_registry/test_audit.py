from datetime import datetime, timezone
import json
from pathlib import Path

from ai_toolkit.agent_registry.audit import AuditEventStore
from ai_toolkit.agent_registry.models import AuditEvent


def _event(repository_id: str, sequence: int) -> AuditEvent:
    return AuditEvent(
        datetime(2026, 1, 1, 12, 0, sequence, tzinfo=timezone.utc),
        "register",
        repository_id,
        "1",
        "success",
        float(sequence),
        {"sequence": sequence, "output": "normal output"},
    )


def test_audit_append_read_preserves_order_and_filters_repository(
    tmp_path: Path,
) -> None:
    audit = AuditEventStore(tmp_path / "audit.ndjson")
    audit.append(_event("alpha", 1))
    audit.append(_event("beta", 2))
    audit.append(_event("alpha", 3))

    report = audit.read()
    selected = audit.read("alpha")

    assert [event.repository_id for event in report.events] == [
        "alpha",
        "beta",
        "alpha",
    ]
    assert [event.metadata["sequence"] for event in selected.events] == [1, 3]
    assert report.is_valid


def test_audit_reports_malformed_lines_without_dropping_valid_events(
    tmp_path: Path,
) -> None:
    path = tmp_path / "audit.ndjson"
    audit = AuditEventStore(path)
    audit.append(_event("alpha", 1))
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{bad}\n")
    audit.append(_event("alpha", 2))

    report = audit.read()

    assert [event.metadata["sequence"] for event in report.events] == [1, 2]
    assert len(report.issues) == 1
    assert "line 2" in report.issues[0].field


def test_audit_reports_unknown_event_fields(tmp_path: Path) -> None:
    path = tmp_path / "audit.ndjson"
    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-01-01T12:00:00Z",
                "operation": "register",
                "repositoryId": "alpha",
                "configurationVersion": "1",
                "outcome": "success",
                "duration": 0.1,
                "metadata": {},
                "extra": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = AuditEventStore(path).read()

    assert not report.events
    assert report.issues


def test_audit_sanitizes_sensitive_metadata_before_persisting(tmp_path: Path) -> None:
    path = tmp_path / "audit.ndjson"
    event = AuditEvent(
        datetime.now(timezone.utc),
        "hook:check",
        "alpha",
        "1",
        "failed",
        0.2,
        {"token": "secret-value", "output": "TOKEN=secret-value"},
    )

    AuditEventStore(path).append(event)

    text = path.read_text(encoding="utf-8")
    assert "secret-value" not in text
    assert '"token"' not in text
