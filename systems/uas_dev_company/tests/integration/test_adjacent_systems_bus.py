"""Интеграция с моками смежных систем через реальный Kafka/MQTT (Задача 16)."""

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

from audit_log.audit_service import AuditLogService, LocalAuditJournalPort
from broker.bus_factory import create_system_bus
from shared.bus_integration_adapters import (
    BusDroneAnalyticsClient,
    BusDronePortClient,
    BusOperatorFleetPort,
    BusRegulatorPort,
)
from analytics_adapter import AnalyticsAdapterService
from certification_service.certification_service import CertificationService
from drone_registry.registry_service import DroneRegistryService
from firmware_ingestion.firmware_service import FirmwareService
from purchase_service.purchase_core import PurchaseService
from user_management.user_service import UserService
from shared.storage import MONOLITH, SQLiteStorage
from shared.topics import Roles

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


@requires_adjacent_bus
def test_agro_chain_with_external_bus_mocks(tmp_path: Path, adjacent_broker_type: str) -> None:
    broker_type = adjacent_broker_type
    if broker_type == "kafka" and not _kafka_configured():
        pytest.skip("KAFKA_BOOTSTRAP_SERVERS not set for host-side pytest")
    if broker_type == "mqtt" and not _mqtt_configured():
        pytest.skip("MQTT_BROKER not set for host-side pytest")

    os.environ["BROKER_TYPE"] = broker_type
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
        client_id=f"adj_mock_{uid}",
    )
    mocks.start()
    time.sleep(3)

    uas_bus = create_system_bus(bus_type=broker_type, client_id=f"uas_side_{uid}")
    uas_bus.start()
    try:
        reg_ad = BusRegulatorPort(bus=uas_bus, timeout=90.0)
        op_ad = BusOperatorFleetPort(bus=uas_bus, timeout=90.0)
        port_ad = BusDronePortClient(bus=uas_bus, timeout=90.0)
        analytics_ad = BusDroneAnalyticsClient(bus=uas_bus, timeout=60.0)

        storage = SQLiteStorage(MONOLITH, db_path=tmp_path / "bus.sqlite3")
        central = AnalyticsAdapterService(
            storage, enabled=True, url="http://unused", api_key="k", client=analytics_ad
        )
        sink = LocalAuditJournalPort(AuditLogService(storage, central_journal=central))

        users = UserService(storage, security_journal=sink)
        admin = users.bootstrap_admin("admin", "adm")
        dev = users.create_user(admin["role"], "dev-agro", Roles.DEVELOPER, "d")
        op = users.create_user(admin["role"], "op-agro", Roles.OPERATOR, "o")

        firmware = FirmwareService(storage, security_journal=sink)
        cert_svc = CertificationService(storage, regulator=reg_ad, security_journal=sink)
        reg_svc = DroneRegistryService(storage, regulator=reg_ad, security_journal=sink, operator_fleet=fake_op)

        submitted = firmware.submit(
            Roles.DEVELOPER,
            dev["username"],
            {
                "firmware_id": "fw-agro-bus",
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
        c = cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-agro-bus")
        r = reg_svc.register(
            Roles.DEVELOPER,
            {
                "serial_number": "AGRO-BUS-001",
                "drone_type": "agrodrone",
                "firmware_id": "fw-agro-bus",
                "certificate_id": c["certificate_id"],
                "security_goals": ["ЦБ-1"],
                "price": 750000,
            },
        )
        assert r["registration_status"] == "registered_by_regulator"

        purchase = PurchaseService(
            storage,
            regulator=reg_ad,
            security_journal=sink,
            operator_fleet=op_ad,
            drone_port=port_ad,
            registry=reg_svc,
        )
        order = purchase.purchase(
            Roles.OPERATOR,
            op["username"],
            "AGRO-BUS-001",
            destination_droneport_id="DP-01",
        )
        assert order["purchased"] is True
        assert "AGRO-BUS-001" in fake_op.drones
        assert port.envelopes, "drone port should receive delivery envelope"

        types = [e.get("event_type") for e in journal.events if isinstance(e, dict)]
        assert "event" in types
    finally:
        uas_bus.stop()
        mocks.stop()


@requires_adjacent_bus
def test_regulator_bus_rejects_bad_contract(tmp_path: Path, adjacent_broker_type: str) -> None:
    broker_type = adjacent_broker_type
    if broker_type == "kafka" and not _kafka_configured():
        pytest.skip("KAFKA_BOOTSTRAP_SERVERS not set")
    if broker_type == "mqtt" and not _mqtt_configured():
        pytest.skip("MQTT_BROKER not set")

    os.environ["BROKER_TYPE"] = broker_type
    uid = uuid.uuid4().hex[:10]
    fake_reg = FakeRegulator()
    stubs_op = FakeOperatorRegistry()
    mocks = AdjacentBusMocks(
        broker_type=broker_type,
        fake_regulator=fake_reg,
        fake_operator=stubs_op,
        fake_drone_port=None,
        fake_analytics=None,
        client_id=f"adj_mock_bad_{uid}",
    )
    mocks.start()
    time.sleep(3)
    uas_bus = create_system_bus(bus_type=broker_type, client_id=f"uas_bad_{uid}")
    uas_bus.start()
    try:
        reg_ad = BusRegulatorPort(bus=uas_bus, timeout=60.0)
        bad = {
            "schema_version": "wrong-schema",
            "correlation_id": "x",
            "sender": "systems.uas_dev_company",
            "actor": "u",
            "timestamp": "2026-01-01T00:00:00Z",
            "payload": {
                "firmware_id": "fw",
                "supplier": "s",
                "drone_type": "d",
                "version": "1",
                "security_goals": ["ЦБ-1"],
                "authenticity_proof": "p",
            },
        }
        with pytest.raises(ValueError, match="contract|schema"):
            reg_ad.certify_firmware(bad)
    finally:
        uas_bus.stop()
        mocks.stop()
