"""
Точка входа: python -m components.

Переменные окружения (единая шина SystemBus, как у систем):
  COMPONENT_ID     — идентификатор экземпляра (dummy_component_a → тип dummy_component)
  BROKER_TYPE      — kafka или mqtt (из docker/.env)
  KAFKA_BOOTSTRAP_SERVERS, MQTT_BROKER, MQTT_PORT — адрес брокера
  BROKER_USER, BROKER_PASSWORD — SASL/MQTT auth
"""
import os
import sys

from broker.bus_factory import create_system_bus
from components.dummy_component.src.dummy_component import DummyComponent


def _component_id_to_type(component_id: str) -> str:
    """dummy_component_a -> dummy_component."""
    s = component_id.strip().lower()
    if "_" in s:
        return s.rsplit("_", 1)[0]
    return s


def main():
    component_id = os.environ.get("COMPONENT_ID", "").strip()
    if not component_id:
        print("COMPONENT_ID is required (e.g. dummy_component_a)", file=sys.stderr)
        sys.exit(1)

    component_type = _component_id_to_type(component_id)
    name = os.environ.get("COMPONENT_NAME", component_id.replace("_", " ").title())

    if component_type and component_type != "dummy_component":
        print(f"Unknown COMPONENT_TYPE: {component_type}", file=sys.stderr)
        sys.exit(1)

    bus = create_system_bus(client_id=component_id)
    component = DummyComponent(
        component_id=component_id,
        name=name,
        bus=bus,
    )
    component.start()

    print(f"[{component_id}] Running. Press Ctrl+C to stop.")

    import signal
    def signal_handler(sig, frame):
        print(f"\n[{component_id}] Received signal {sig}, shutting down...")
        component.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while component._running:
            signal.pause()
    except AttributeError:
        import time
        while component._running:
            time.sleep(1)


if __name__ == "__main__":
    main()
