"""Клиент proxy_request к security_monitor для междоменных вызовов воркеров (Задача 22)."""

from __future__ import annotations

import os
from typing import Any

from broker.system_bus import SystemBus

from shared.monitor_proxy_unwrap import BusInvocationError, unwrap_monitor_proxy_result
from shared.topics import Actions, ComponentTopics


def monitor_proxy(
    bus: SystemBus,
    sender_topic: str,
    target_topic: str,
    target_action: str,
    data: dict[str, Any],
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    to = float(
        timeout
        if timeout is not None
        else os.environ.get("WORKER_MONITOR_PROXY_TIMEOUT_S", os.environ.get("SECURITY_MONITOR_PROXY_REQUEST_TIMEOUT_S", "30"))
    )
    message = {
        "action": Actions.PROXY_REQUEST,
        "sender": sender_topic,
        "payload": {
            "target": {"topic": target_topic, "action": target_action},
            "data": data,
        },
    }
    raw = bus.request(ComponentTopics.SECURITY_MONITOR, message, timeout=to)
    return unwrap_monitor_proxy_result(raw)


__all__ = ["monitor_proxy", "BusInvocationError"]
