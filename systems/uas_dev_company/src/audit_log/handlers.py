"""Обработчики сообщений audit_log."""

from __future__ import annotations

import os
from typing import Any, Callable

from shared.models import SecurityEvent
from audit_log.audit_service import AuditLogService
from shared.storage import SQLiteStorage
from shared.tcb import security_event_to_analytics_payload
from shared.topics import Actions
from shared.worker_deps import WorkerServiceDeps


def build_audit_log_handlers(
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    audit = AuditLogService(storage)

    def record_audit(payload: dict[str, Any]) -> dict[str, Any]:
        ev = payload.get("event") if isinstance(payload.get("event"), dict) else {}
        event = SecurityEvent(
            str(ev["event_type"]),
            str(ev["severity"]),
            str(ev["source"]),
            str(ev["subject"]),
            str(ev.get("details") or ""),
        )
        result = audit.log(event)
        if deps.analytics:
            inst = os.environ.get("COMPONENT_ID", "").strip() or None
            deps.analytics.try_emit(security_event_to_analytics_payload(event, instance_id_override=inst))
        return result

    return {Actions.RECORD_AUDIT: record_audit}
