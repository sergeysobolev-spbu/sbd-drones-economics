"""Точка входа: python -m systems. SYSTEM_TYPE из окружения."""
import os
import sys

from broker.bus_factory import create_system_bus
from systems.dummy_system.src.dummy import DummySystem


def main():
    system_type = os.environ.get("SYSTEM_TYPE", "").strip().lower()
    system_id = os.environ.get("SYSTEM_ID", "dummy_001")
    health_port = int(os.environ.get("HEALTH_PORT", "0") or "0")
    name = os.environ.get("SYSTEM_NAME", system_id.replace("_", " ").title())

    if system_type and system_type != "dummy":
        print("SYSTEM_TYPE must be 'dummy'", file=sys.stderr)
        sys.exit(1)

    bus = create_system_bus(client_id=system_id)
    system = DummySystem(
        system_id=system_id,
        name=name,
        bus=bus,
        health_port=health_port or None,
    )
    system.run_forever()


if __name__ == "__main__":
    main()
