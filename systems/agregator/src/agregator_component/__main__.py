"""Точка входа для компонента агрегатора."""
import os
import sys
import signal
import time

from broker.bus_factory import create_system_bus
from systems.agregator.src.agregator_component.src.agregator_component import AgregatorComponent


def main():
    component_id = os.environ.get("COMPONENT_ID", "agregator_component")

    bus = create_system_bus(client_id=component_id)
    component = AgregatorComponent(
        component_id=component_id,
        bus=bus,
    )
    component.start()

    print(f"[{component_id}] Running. Press Ctrl+C to stop.")

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
        while component._running:
            time.sleep(1)


if __name__ == "__main__":
    main()
