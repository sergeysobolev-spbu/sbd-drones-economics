"""
Демо: запрос на валидацию через SecurityMonitor.

Используется для ручной проверки работы `SecurityMonitorActions.VALIDATE_REQUEST`.
"""

from __future__ import annotations

import os
import uuid

from broker.src.bus_factory import create_system_bus
from systems.operator.src.topics import ComponentTopics, SecurityMonitorActions


def main() -> int:
    broker_type = os.getenv("BROKER_TYPE", "mqtt")
    system_id = os.getenv("SYSTEM_ID", "operator-001")
    client_id = f"{system_id}.demo-security.{uuid.uuid4().hex[:8]}"

    bus = create_system_bus(bus_type=broker_type, client_id=client_id)
    bus.start()

    security_topic = ComponentTopics.get_security_monitor()

    # SecurityMonitor ждёт: payload.request + payload.sender_role.
    message = {
        "action": SecurityMonitorActions.VALIDATE_REQUEST,
        "sender": "demo-security-client",
        "payload": {
            "request": {
                "action": "receive_order",
                "sender": "aggregator-demo",
            },
            "context": {},
            "sender_role": "operator",
            "target_component": "operator_system",
        },
    }

    resp = bus.request(security_topic, message, timeout=10.0)
    if not resp:
        print("No response from security-monitor.")
        return 1

    print("SecurityMonitor response payload:")
    print(resp.get("payload", {}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

