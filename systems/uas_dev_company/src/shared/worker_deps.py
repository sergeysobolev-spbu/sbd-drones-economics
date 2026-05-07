"""Зависимости доменных воркеров (порты смежных систем + analytics IPC)."""

from __future__ import annotations

from dataclasses import dataclass

from broker.system_bus import SystemBus

from analytics_adapter.protocol import SupportsAnalyticsEmit
from shared.analytics_ipc import make_analytics_ipc_emitter
from shared.audit_log_ipc import SupportsSecurityJournal, make_security_journal_ipc_forwarder
from shared.external_adapters_factory import create_external_system_ports
from shared.integration_adapters import DronePortPort, OperatorFleetPort, RegulatorPort
from shared.topics import ComponentTopics


@dataclass
class WorkerServiceDeps:
    bus: SystemBus
    self_topic: str
    regulator: RegulatorPort | None = None
    operator_fleet: OperatorFleetPort | None = None
    drone_port: DronePortPort | None = None
    analytics: SupportsAnalyticsEmit | None = None
    security_journal: SupportsSecurityJournal | None = None


def build_worker_service_deps(bus: SystemBus, self_topic: str, component_id: str) -> WorkerServiceDeps:
    if self_topic == ComponentTopics.ANALYTICS_ADAPTER:
        reg, op, dp = None, None, None
    else:
        reg, op, dp = create_external_system_ports(component_id, bus)
    analytics = make_analytics_ipc_emitter(bus, self_topic)
    security_journal = make_security_journal_ipc_forwarder(bus, self_topic)
    return WorkerServiceDeps(
        bus=bus,
        self_topic=self_topic,
        regulator=reg,
        operator_fleet=op,
        drone_port=dp,
        analytics=analytics,
        security_journal=security_journal,
    )
