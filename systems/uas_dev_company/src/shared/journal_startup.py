"""Стартовые записи в журнал безопасности / центральный журнал для процессов UAS."""

from __future__ import annotations

import os

from shared.audit_log_ipc import make_security_journal_ipc_forwarder
from shared.models import SecurityEvent
from shared.services import AuditLogService
from shared.storage import SQLiteStorage
from shared.tcb.journal_policy import security_event_to_analytics_payload
from shared.topics import ComponentTopics
from shared.worker_deps import WorkerServiceDeps


def emit_worker_process_startup(
    *,
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
    component_id: str,
    component_type: str,
    topic: str,
) -> None:
    """Одно событие worker_started после подписки воркера на шину."""
    ev = SecurityEvent(
        "worker_started",
        "info",
        component_type,
        component_id,
        f"topic={topic}",
    )
    inst = os.environ.get("COMPONENT_ID", "").strip() or component_id
    payload = security_event_to_analytics_payload(ev, instance_id_override=inst)
    if deps.security_journal is not None:
        deps.security_journal.try_record(ev)
        return
    if deps.self_topic == ComponentTopics.AUDIT_LOG:
        AuditLogService(storage).log(ev)
        if deps.analytics is not None:
            deps.analytics.try_emit(payload)
        return
    if deps.self_topic == ComponentTopics.ANALYTICS_ADAPTER:
        from analytics_adapter.service import analytics_adapter_service_from_env

        svc = analytics_adapter_service_from_env(storage, deps.bus)
        svc.try_emit(payload)


def emit_api_gateway_sqlite_started(audit: AuditLogService) -> None:
    """Режим sqlite: запись через AuditLogService (включая central_journal при настройке)."""
    cid = os.environ.get("COMPONENT_ID", "").strip() or "api_gateway"
    audit.log(
        SecurityEvent(
            "worker_started",
            "info",
            "api_gateway",
            cid,
            "UAS_GATEWAY_BACKEND=sqlite",
        )
    )


def emit_api_gateway_bus_started(bus) -> None:
    """Режим bus: fire-and-forget в audit_log через IPC."""
    fj = make_security_journal_ipc_forwarder(bus, ComponentTopics.API_GATEWAY)
    if fj is None:
        return
    cid = os.environ.get("COMPONENT_ID", "").strip() or "api_gateway"
    fj.try_record(
        SecurityEvent(
            "worker_started",
            "info",
            "api_gateway",
            cid,
            "UAS_GATEWAY_BACKEND=bus",
        )
    )


def emit_security_monitor_started(bus) -> None:
    fj = make_security_journal_ipc_forwarder(bus, ComponentTopics.SECURITY_MONITOR)
    if fj is None:
        return
    cid = os.environ.get("COMPONENT_ID", "").strip() or "security_monitor"
    fj.try_record(
        SecurityEvent(
            "worker_started",
            "info",
            "security_monitor",
            cid,
            "security_monitor process",
        )
    )
