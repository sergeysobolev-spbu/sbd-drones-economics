"""Минимальные записи в audit_log по шине без зависимостей от worker_deps (Задача 23 — узкий образ security_monitor / gateway bus)."""

from __future__ import annotations

import os

from shared.audit_log_ipc import make_security_journal_ipc_forwarder
from shared.models import SecurityEvent
from shared.topics import ComponentTopics


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
