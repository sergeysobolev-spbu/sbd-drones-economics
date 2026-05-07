"""Задача 17: IPC к analytics_adapter и выход на systems.drone_analytics через реальный брокер."""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

import pytest

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeDroneAnalytics, FakeDronePort, FakeOperatorRegistry, FakeRegulator

from analytics_adapter.handlers import build_analytics_adapter_handlers
from audit_log.handlers import build_audit_log_handlers
from broker.bus_factory import create_system_bus
from shared.audit_log_ipc import AuditLogIpcForwarder
from shared.bus_integration_adapters import BusDronePortClient, BusOperatorFleetPort, BusRegulatorPort
from shared.component_base import ServiceComponent
from shared.services import (
    CertificationService,
    DroneRegistryService,
    FirmwareService,
    PurchaseService,
    UserService,
)
from shared.storage import SQLiteStorage
from shared.topics import ComponentTopics, Roles
from shared.worker_deps import WorkerServiceDeps, build_worker_service_deps

from bus_adjacent_mocks import AdjacentBusMocks

requires_adjacent_bus = pytest.mark.skipif(
    not os.environ.get("UAS_ADJACENT_BUS_INTEGRATION"),
    reason="Set UAS_ADJACENT_BUS_INTEGRATION=1 and broker env (see make bus-adjacent-test)",
)


def _adjacent_broker_types() -> list[str]:
    raw = os.environ.get("UAS_ADJACENT_BROKER_TYPES", "kafka,mqtt")
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def _kafka_configured() -> bool:
    return bool(os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "").strip())


def _mqtt_configured() -> bool:
    return bool(os.environ.get("MQTT_BROKER", "").strip())


@pytest.fixture(params=_adjacent_broker_types())
def adjacent_broker_type(request: pytest.FixtureRequest) -> str:
    return str(request.param)


_AN_TRUSTED = frozenset(
    {
        ComponentTopics.CERTIFICATION_SERVICE,
        ComponentTopics.DRONE_REGISTRY,
        ComponentTopics.PURCHASE_SERVICE,
        ComponentTopics.AUDIT_LOG,
    },
)


_AUDIT_TRUSTED = frozenset(
    {
        ComponentTopics.SECURITY_MONITOR,
        ComponentTopics.USER_MANAGEMENT,
        ComponentTopics.FIRMWARE_INGESTION,
        ComponentTopics.CERTIFICATION_SERVICE,
        ComponentTopics.DRONE_REGISTRY,
        ComponentTopics.PURCHASE_SERVICE,
    }
)


@requires_adjacent_bus
def test_analytics_ipc_worker_reaches_external_journal(
    tmp_path: Path,
    adjacent_broker_type: str,
) -> None:
    broker_type = adjacent_broker_type
    if broker_type == "kafka" and not _kafka_configured():
        pytest.skip("KAFKA_BOOTSTRAP_SERVERS not set for host-side pytest")
    if broker_type == "mqtt" and not _mqtt_configured():
        pytest.skip("MQTT_BROKER not set for host-side pytest")

    prev = {
        "DRONE_ANALYTICS_ENABLED": os.environ.get("DRONE_ANALYTICS_ENABLED"),
        "UAS_DRONE_ANALYTICS_TRANSPORT": os.environ.get("UAS_DRONE_ANALYTICS_TRANSPORT"),
        "UAS_EXTERNAL_SYSTEMS_TRANSPORT": os.environ.get("UAS_EXTERNAL_SYSTEMS_TRANSPORT"),
        "BROKER_TYPE": os.environ.get("BROKER_TYPE"),
    }
    os.environ["BROKER_TYPE"] = broker_type
    os.environ["DRONE_ANALYTICS_ENABLED"] = "true"
    os.environ["UAS_DRONE_ANALYTICS_TRANSPORT"] = "bus"
    os.environ["UAS_EXTERNAL_SYSTEMS_TRANSPORT"] = "bus"

    uid = uuid.uuid4().hex[:10]
    fake_reg = FakeRegulator()
    fake_op = FakeOperatorRegistry()
    port = FakeDronePort(valid_ports={"DP-01"})
    journal = FakeDroneAnalytics()
    mocks = AdjacentBusMocks(
        broker_type=broker_type,
        fake_regulator=fake_reg,
        fake_operator=fake_op,
        fake_drone_port=port,
        fake_analytics=journal,
        client_id=f"adj_mock_an_{uid}",
    )
    mocks.start()
    time.sleep(3)

    uas_bus = create_system_bus(bus_type=broker_type, client_id=f"uas_an_{uid}")
    uas_bus.start()
    analytics_comp: ServiceComponent | None = None
    audit_comp: ServiceComponent | None = None
    try:
        storage = SQLiteStorage(tmp_path / "ipc_an.sqlite3")
        deps_ax = WorkerServiceDeps(
            bus=uas_bus,
            self_topic=ComponentTopics.ANALYTICS_ADAPTER,
        )
        handlers = build_analytics_adapter_handlers(storage, deps_ax)
        analytics_comp = ServiceComponent(
            component_id=f"analytics_{uid}",
            component_type="analytics_adapter",
            topic=ComponentTopics.ANALYTICS_ADAPTER,
            bus=uas_bus,
            handlers=handlers,
            trusted_sender=_AN_TRUSTED,
        )
        analytics_comp.start()
        time.sleep(2)

        deps_audit = build_worker_service_deps(uas_bus, ComponentTopics.AUDIT_LOG, f"audit_{uid}")
        handlers_audit = build_audit_log_handlers(storage, deps_audit)
        audit_comp = ServiceComponent(
            component_id=f"audit_{uid}",
            component_type="audit_log",
            topic=ComponentTopics.AUDIT_LOG,
            bus=uas_bus,
            handlers=handlers_audit,
            trusted_sender=_AUDIT_TRUSTED,
        )
        audit_comp.start()
        time.sleep(1)

        reg_ad = BusRegulatorPort(bus=uas_bus, timeout=90.0)
        op_ad = BusOperatorFleetPort(bus=uas_bus, timeout=90.0)
        port_ad = BusDronePortClient(bus=uas_bus, timeout=90.0)

        cert_svc = CertificationService(
            storage,
            regulator=reg_ad,
            security_journal=AuditLogIpcForwarder(uas_bus, ComponentTopics.CERTIFICATION_SERVICE),
        )
        reg_svc = DroneRegistryService(
            storage,
            regulator=reg_ad,
            security_journal=AuditLogIpcForwarder(uas_bus, ComponentTopics.DRONE_REGISTRY),
            operator_fleet=op_ad,
        )
        purchase_svc = PurchaseService(
            storage,
            regulator=reg_ad,
            security_journal=AuditLogIpcForwarder(uas_bus, ComponentTopics.PURCHASE_SERVICE),
            operator_fleet=op_ad,
            drone_port=port_ad,
        )

        users = UserService(
            storage,
            security_journal=AuditLogIpcForwarder(uas_bus, ComponentTopics.USER_MANAGEMENT),
        )
        admin = users.bootstrap_admin("admin", "adm")
        dev = users.create_user(admin["role"], "dev-an-ipc", Roles.DEVELOPER, "d")
        op = users.create_user(admin["role"], "op-an-ipc", Roles.OPERATOR, "o")

        firmware = FirmwareService(
            storage,
            security_journal=AuditLogIpcForwarder(uas_bus, ComponentTopics.FIRMWARE_INGESTION),
        )
        submitted = firmware.submit(
            Roles.DEVELOPER,
            dev["username"],
            {
                "firmware_id": "fw-an-ipc",
                "supplier": "itmoniks",
                "drone_type": "agrodrone",
                "version": "master-4c6ed55",
                "firmware_hash": "",
                "source_repo_url": "https://gitflic.ru/project/itmoniks/cyber_drons/commit?branch=master",
                "source_commit": "4c6ed55bfcf34b84a0ac669100b1bf8835785d98",
                "security_goals": ["ЦБ-1", "ЦБ-3"],
                "authenticity_proof": "gitflic-source-commit",
            },
        )
        assert submitted["accepted"] is True
        c = cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-an-ipc")
        reg_svc.register(
            Roles.DEVELOPER,
            {
                "serial_number": "AN-IPC-001",
                "drone_type": "agrodrone",
                "firmware_id": "fw-an-ipc",
                "certificate_id": c["certificate_id"],
                "security_goals": ["ЦБ-1"],
                "price": 750000,
            },
        )
        purchase_svc.purchase(
            Roles.OPERATOR,
            op["username"],
            "AN-IPC-001",
            destination_droneport_id="DP-01",
        )

        assert journal.events, "external DroneAnalytics mock should receive events via audit_log → analytics_adapter"
    finally:
        if audit_comp is not None:
            audit_comp.stop()
        if analytics_comp is not None:
            analytics_comp.stop()
        uas_bus.stop()
        mocks.stop()
        for key, val in prev.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
