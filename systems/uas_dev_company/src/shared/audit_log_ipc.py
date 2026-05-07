"""IPC в воркер audit_log (RECORD_AUDIT); fire-and-forget с подавлением ошибок."""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Protocol

from broker.system_bus import SystemBus

from shared.models import SecurityEvent
from shared.topics import Actions, ComponentTopics


class SupportsSecurityJournal(Protocol):
    def try_record(self, event: SecurityEvent) -> None: ...


class AuditLogIpcForwarder:
    """Доменный RPC: ``record_audit`` на топик ``AUDIT_LOG``."""

    def __init__(self, bus: SystemBus, sender_topic: str, *, timeout: float = 5.0):
        self._bus = bus
        self._sender_topic = sender_topic
        self._timeout = timeout

    def try_record(self, event: SecurityEvent) -> None:
        try:
            self._bus.request(
                ComponentTopics.AUDIT_LOG,
                {
                    "action": Actions.RECORD_AUDIT,
                    "sender": self._sender_topic,
                    "payload": {"event": asdict(event)},
                },
                timeout=self._timeout,
            )
        except Exception:
            pass


def make_security_journal_ipc_forwarder(
    bus: SystemBus,
    sender_topic: str,
) -> AuditLogIpcForwarder | None:
    """При выключенном флаге — без RPC (например, учебные тесты без журнала)."""
    if sender_topic in (ComponentTopics.AUDIT_LOG, ComponentTopics.ANALYTICS_ADAPTER):
        return None
    raw = os.environ.get("UAS_SECURITY_JOURNAL_IPC", "true").strip().lower()
    if raw in ("", "0", "false", "no", "off"):
        return None
    return AuditLogIpcForwarder(bus, sender_topic)
