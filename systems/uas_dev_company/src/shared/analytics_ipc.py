"""IPC к воркеру analytics_adapter с процесса домена."""

from __future__ import annotations

import os
from typing import Any

from broker.system_bus import SystemBus

from shared.topics import Actions, ComponentTopics


class AnalyticsIpcForwarder:
    """Тонкий RPC: ``send_analytics`` на топик компонента analytics_adapter."""

    def __init__(self, bus: SystemBus, sender_topic: str, *, timeout: float = 30.0):
        self._bus = bus
        self._sender_topic = sender_topic
        self._timeout = timeout

    def try_emit(self, event: dict[str, Any]) -> None:
        try:
            self._bus.request(
                ComponentTopics.ANALYTICS_ADAPTER,
                {
                    "action": Actions.SEND_ANALYTICS,
                    "sender": self._sender_topic,
                    "payload": {"event": event},
                },
                timeout=self._timeout,
            )
        except Exception:
            pass


def make_analytics_ipc_emitter(
    bus: SystemBus,
    sender_topic: str,
) -> AnalyticsIpcForwarder | None:
    """При включённом журнале — клиент IPC; иначе без RPC (политика окружения)."""
    if sender_topic == ComponentTopics.ANALYTICS_ADAPTER:
        return None
    raw = os.environ.get("DRONE_ANALYTICS_ENABLED", "false").strip().lower()
    if raw in ("", "0", "false", "no", "off"):
        return None
    return AnalyticsIpcForwarder(bus, sender_topic)
