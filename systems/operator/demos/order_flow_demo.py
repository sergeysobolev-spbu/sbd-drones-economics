"""
Демо: полный цикл обработки заказа через OperatorSystem.

Ожидает, что в docker-compose стеке уже запущены:
`operator-system`, `security-monitor`, `fleet-manager`, `mission-planner`, `business-logic`
и брокер (MQTT или Kafka) доступен.
"""

from __future__ import annotations

import os
import time
import uuid

from broker.src.bus_factory import create_system_bus
from systems.operator.src.topics import SystemTopics


def main() -> int:
    broker_type = os.getenv("BROKER_TYPE", "mqtt")
    system_id = os.getenv("SYSTEM_ID", "operator-001")

    # Уникальный client_id, чтобы request/reply не конфликтовали с другими демо.
    client_id = f"{system_id}.demo-order-flow.{uuid.uuid4().hex[:8]}"
    bus = create_system_bus(bus_type=broker_type, client_id=client_id)
    bus.start()

    operator_topic = SystemTopics.get_operator()

    # Сообщение формата для BaseComponent routing: action + payload + sender.
    trace_id = f"demo-trace-{int(time.time())}"
    message = {
        "action": "receive_order",
        "sender": "aggregator-demo",
        "trace_id": trace_id,
        "span_id": str(uuid.uuid4()),
        "parent_span_id": None,
        "payload": {
            "order": {
                "id": f"ORDER-DEMO-{int(time.time())}",
                "type": "cargo_delivery",
                "start_location": {"lat": 55.7558, "lon": 37.6173},
                "end_location": {"lat": 55.76, "lon": 37.62},
                "payload_weight": 3.0,
                "payload_value": 5000.0,
                "start_time": "2026-03-16T17:00:00Z",
                "end_time": "2026-03-16T19:00:00Z",
            }
        },
    }

    resp = bus.request(operator_topic, message, timeout=30.0)
    if not resp:
        print("No response from operator-system (timeout or publish failure).")
        return 1

    payload = resp.get("payload", {})
    print("Operator response payload:")
    print(payload)

    if not resp.get("success", True):
        print("Operator request failed:", resp.get("error"))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

