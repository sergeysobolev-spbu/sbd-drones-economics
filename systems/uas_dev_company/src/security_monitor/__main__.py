"""Точка входа процесса security_monitor."""

from __future__ import annotations

import time

from broker.bus_factory import create_system_bus

from shared.journal_startup import emit_security_monitor_started
from shared.security_monitor import SecurityMonitorComponent


def main() -> None:
    """Запуск security monitor на сконфигурированном брокере."""
    bus = create_system_bus(client_id="uas_dev_company_security_monitor")
    component = SecurityMonitorComponent(component_id="security_monitor", bus=bus)
    component.start()
    emit_security_monitor_started(bus)
    try:
        while True:
            time.sleep(1)
    finally:
        component.stop()


if __name__ == "__main__":
    main()
