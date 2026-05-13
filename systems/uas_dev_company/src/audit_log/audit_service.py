"""Локальный журнал событий безопасности."""

from __future__ import annotations

import os
from typing import Any

from shared.protocols import SupportsAnalyticsEmit

from shared.models import SecurityEvent
from shared.storage import SQLiteStorage
from shared.tcb.journal_policy import security_event_to_analytics_payload


class LocalAuditJournalPort:
    """Публикация в журнал через тот же AuditLogService (sqlite / in-process)."""

    def __init__(self, audit: AuditLogService):
        self._audit = audit

    def try_record(self, event: SecurityEvent) -> None:
        try:
            self._audit.log(event)
        except Exception:
            pass


class AuditLogService:
    """Persist security events locally."""

    def __init__(
        self,
        storage: SQLiteStorage,
        central_journal: SupportsAnalyticsEmit | None = None,
    ):
        self.storage = storage
        self._central_journal = central_journal

    def log(self, event: SecurityEvent) -> dict[str, Any]:
        """Store a security event."""
        with self.storage.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO security_events(event_type, severity, source, subject, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event.event_type, event.severity, event.source, event.subject, event.details),
            )
        result = {"event_id": cursor.lastrowid, "event_type": event.event_type}
        if self._central_journal is not None:
            try:
                inst = os.environ.get("COMPONENT_ID", "").strip() or None
                self._central_journal.try_emit(
                    security_event_to_analytics_payload(event, instance_id_override=inst),
                )
            except Exception:
                pass
        return result

    def list_events(self) -> list[dict[str, Any]]:
        """Return all events in creation order."""
        with self.storage.connect() as connection:
            rows = connection.execute("SELECT * FROM security_events ORDER BY id").fetchall()
        return [dict(row) for row in rows]
