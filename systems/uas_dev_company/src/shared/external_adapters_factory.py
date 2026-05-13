"""Фабрика портов смежных систем для воркеров (HTTP off / шина SystemBus)."""

from __future__ import annotations

import os

from broker.system_bus import SystemBus

from shared.bus_integration_adapters import BusDronePortClient, BusOperatorFleetPort, BusRegulatorPort
from shared.integration_adapters import DronePortPort, OperatorFleetPort, RegulatorPort


def create_external_system_ports(
    worker_component_id: str,
    bus: SystemBus,
) -> tuple[RegulatorPort | None, OperatorFleetPort | None, DronePortPort | None]:
    """При ``UAS_EXTERNAL_SYSTEMS_TRANSPORT=bus`` вернуть адаптеры на общей шине процесса (тот же ``bus``, что у воркера)."""
    mode = os.environ.get("UAS_EXTERNAL_SYSTEMS_TRANSPORT", "none").strip().lower()
    if mode != "bus":
        return None, None, None
    cid = f"{worker_component_id}_ext"
    return (
        BusRegulatorPort(bus=bus, client_id=f"{cid}_regulator"),
        BusOperatorFleetPort(bus=bus, client_id=f"{cid}_operator"),
        BusDronePortClient(bus=bus, client_id=f"{cid}_drone_port"),
    )
