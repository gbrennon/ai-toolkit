from collections.abc import Mapping, Sequence
import json
from pathlib import Path

from .audit_sanitizer import sanitize_metadata
from .errors import MalformedDocumentError
from .models import AuditEvent, AuditReadReport, ValidationIssue
from .models._json import JsonValue
from .ndjson_event_store import NdjsonEventStore

def _append_event(
    store: NdjsonEventStore, path: Path, event: dict[str, JsonValue]
) -> None:
    store.append(path, event)


class AuditEventStore:
    """Append, parse, filter, and report issues in one audit NDJSON file."""

    def __init__(self, path: Path, store: NdjsonEventStore | None = None) -> None:
        self._path = path
        self._store = NdjsonEventStore() if store is None else store

    def append(self, event: AuditEvent) -> None:
        """Append one sanitized and strictly validated event in order."""
        validated = AuditEvent(
            event.timestamp,
            event.operation,
            event.repository_id,
            event.configuration_version,
            event.outcome,
            event.duration,
            sanitize_metadata(event.metadata),
        )
        _append_event(self._store, self._path, validated.to_json())

    def record(self, event: AuditEvent) -> None:
        """Persist one event through the audit sink protocol."""
        self.append(event)

    def read(self, repository_id: str | None = None) -> AuditReadReport:
        """Read events in append order and return all malformed-line issues."""
        if not self._path.exists():
            return AuditReadReport()
        try:
            raw_events = self._store.read(self._path)
        except MalformedDocumentError:
            return self._read_lines(repository_id)
        return self._parse_events(raw_events, repository_id)

    def _parse_events(
        self, raw_events: Sequence[Mapping[str, JsonValue]], repository_id: str | None
    ) -> AuditReadReport:
        events: list[AuditEvent] = []
        issues: list[ValidationIssue] = []
        for line_number, raw_event in enumerate(raw_events, start=1):
            event, issue = _decode_event(raw_event, line_number, self._path)
            if issue is not None:
                issues.append(issue)
            elif event is not None and _selected(event, repository_id):
                events.append(event)
        return AuditReadReport(tuple(events), tuple(issues))

    def _read_lines(self, repository_id: str | None) -> AuditReadReport:
        try:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as error:
            return AuditReadReport((), (self._issue(1, str(error)),))
        return self._parse_lines(lines, repository_id)

    def _parse_lines(
        self, lines: Sequence[str], repository_id: str | None
    ) -> AuditReadReport:
        events: list[AuditEvent] = []
        issues: list[ValidationIssue] = []
        for line_number, line in enumerate(lines, start=1):
            event, issue = _decode_line(line, line_number, self._path)
            if issue is not None:
                issues.append(issue)
            elif event is not None and _selected(event, repository_id):
                events.append(event)
        return AuditReadReport(tuple(events), tuple(issues))

    def _issue(self, line_number: int, message: str) -> ValidationIssue:
        return ValidationIssue(
            f"{self._path}:line {line_number}", "malformed-audit-event", message
        )


def _decode_event(
    raw_event: Mapping[str, JsonValue], line_number: int, path: Path
) -> tuple[AuditEvent | None, ValidationIssue | None]:
    try:
        return AuditEvent.from_json(raw_event), None
    except (TypeError, ValueError) as error:
        return None, ValidationIssue(
            f"{path}:line {line_number}", "malformed-audit-event", str(error)
        )


def _decode_line(
    line: str, line_number: int, path: Path
) -> tuple[AuditEvent | None, ValidationIssue | None]:
    try:
        raw_event = json.loads(line)
        if not isinstance(raw_event, Mapping):
            raise ValueError("record is not a JSON object")
        return _decode_event(raw_event, line_number, path)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        return None, ValidationIssue(
            f"{path}:line {line_number}", "malformed-audit-event", str(error)
        )


def _selected(event: AuditEvent, repository_id: str | None) -> bool:
    return repository_id is None or event.repository_id == repository_id
