"""Точка входа для OperatorComponent."""
import os

from broker.bus_factory import create_system_bus
from systems.operator.src.operator_component.src.operator_component import OperatorComponent


def main() -> None:
    component_id = os.environ.get("COMPONENT_ID", "operator_component")
    bus = create_system_bus(client_id=component_id)
    component = OperatorComponent(component_id=component_id, bus=bus)
    component.start()
    # BaseComponent.start() runs bus and subscriptions; keep process alive.
    import time

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()

