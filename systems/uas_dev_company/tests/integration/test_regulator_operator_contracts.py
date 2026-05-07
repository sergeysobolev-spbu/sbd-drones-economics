"""Интеграционные тесты контрактов Регулятор–Эксплуатант–Дронопорт–DroneAnalytics (моки)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakes import FakeDroneAnalytics, FakeDronePort, FakeOperatorRegistry, FakeRegulator

from audit_log.audit_service import AuditLogService, LocalAuditJournalPort
from shared.services import (
    AnalyticsAdapterService,
    CertificationService,
    CriticalVulnerabilityService,
    DroneRegistryService,
    FirmwareService,
    PurchaseService,
    UserService,
)
from shared.storage import SQLiteStorage
from shared.topics import Roles


def _journal_sink(storage: SQLiteStorage, client: FakeDroneAnalytics) -> LocalAuditJournalPort:
    analytics = AnalyticsAdapterService(storage, enabled=True, url="http://unused", api_key="k", client=client)
    return LocalAuditJournalPort(AuditLogService(storage, central_journal=analytics))


@pytest.fixture()
def storage(tmp_path: Path) -> SQLiteStorage:
    return SQLiteStorage(tmp_path / "integration.sqlite3")


def _bootstrap_dev_op(storage: SQLiteStorage) -> tuple[UserService, dict, dict]:
    users = UserService(storage)
    admin = users.bootstrap_admin("admin", "adm")
    dev = users.create_user(admin["role"], "dev-agro", Roles.DEVELOPER, "d")
    op = users.create_user(admin["role"], "op-agro", Roles.OPERATOR, "o")
    return users, dev, op


def test_agro_gitflic_certify_register_purchase_reregister_import(storage: SQLiteStorage) -> None:
    _, dev, op = _bootstrap_dev_op(storage)
    fake_reg = FakeRegulator()
    fake_op = FakeOperatorRegistry()
    journal = FakeDroneAnalytics()
    sink = _journal_sink(storage, journal)
    firmware = FirmwareService(storage)
    cert_svc = CertificationService(storage, regulator=fake_reg, security_journal=sink)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg, security_journal=sink, operator_fleet=fake_op)

    submitted = firmware.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": "fw-agro-itc",
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
    c = cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-agro-itc")
    r = reg_svc.register(
        Roles.DEVELOPER,
        {
            "serial_number": "AGRO-4C6ED55-001",
            "drone_type": "agrodrone",
            "firmware_id": "fw-agro-itc",
            "certificate_id": c["certificate_id"],
            "security_goals": ["ЦБ-1"],
            "price": 750000,
        },
    )
    assert r["registration_status"] == "registered_by_regulator"

    purchase = PurchaseService(
        storage,
        regulator=fake_reg,
        security_journal=sink,
        operator_fleet=fake_op,
        drone_port=None,
    )
    order = purchase.purchase(Roles.OPERATOR, op["username"], "AGRO-4C6ED55-001")
    assert order["purchased"] is True
    assert "AGRO-4C6ED55-001" in fake_op.drones

    with pytest.raises(ValueError, match="available certified drone"):
        purchase.purchase(Roles.OPERATOR, op["username"], "AGRO-4C6ED55-001")

    types = [e["event_type"] for e in journal.events if e.get("event_type")]
    assert "event" in types


def test_delivery_to_droneport_transfers_physical_responsibility(storage: SQLiteStorage) -> None:
    _, dev, op = _bootstrap_dev_op(storage)
    fake_reg = FakeRegulator()
    fake_op = FakeOperatorRegistry()
    port = FakeDronePort(valid_ports={"DP-01"})
    firmware = FirmwareService(storage)
    cert_svc = CertificationService(storage, regulator=fake_reg)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg, operator_fleet=fake_op)
    firmware.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": "fw-dlv",
            "supplier": "s",
            "drone_type": "agro",
            "version": "1",
            "firmware_hash": "h",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p",
        },
    )
    c = cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-dlv")
    reg_svc.register(
        Roles.DEVELOPER,
        {
            "serial_number": "DLV-1",
            "drone_type": "agro",
            "firmware_id": "fw-dlv",
            "certificate_id": c["certificate_id"],
            "security_goals": ["ЦБ-1"],
            "price": 1,
        },
    )
    purchase = PurchaseService(storage, regulator=fake_reg, operator_fleet=fake_op, drone_port=port)
    out = purchase.purchase(Roles.OPERATOR, op["username"], "DLV-1", destination_droneport_id="DP-01")
    assert out["delivery_status"] == "delivered"
    with storage.connect() as connection:
        row = connection.execute("SELECT physical_safety_responsibility FROM drones WHERE serial_number='DLV-1'").fetchone()
    assert row["physical_safety_responsibility"] == "operator"


def test_broker_payload_to_fake_drone_port_contains_port_id(storage: SQLiteStorage) -> None:
    _, dev, op = _bootstrap_dev_op(storage)
    fake_reg = FakeRegulator()
    fake_op = FakeOperatorRegistry()
    port = FakeDronePort(valid_ports={"P9"})
    firmware = FirmwareService(storage)
    cert_svc = CertificationService(storage, regulator=fake_reg)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg, operator_fleet=fake_op)
    firmware.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": "fw-br",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "x",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p",
        },
    )
    c = cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-br")
    reg_svc.register(
        Roles.DEVELOPER,
        {
            "serial_number": "BR-1",
            "drone_type": "t",
            "firmware_id": "fw-br",
            "certificate_id": c["certificate_id"],
            "security_goals": ["ЦБ-1"],
            "price": 1,
        },
    )
    PurchaseService(storage, regulator=fake_reg, operator_fleet=fake_op, drone_port=port).purchase(
        Roles.OPERATOR, op["username"], "BR-1", destination_droneport_id="P9"
    )
    assert len(port.envelopes) == 1
    assert port.envelopes[0]["payload"]["port_id"] == "P9"


def test_negative_unknown_droneport_keeps_developer_physical_responsibility(storage: SQLiteStorage) -> None:
    _, dev, op = _bootstrap_dev_op(storage)
    fake_reg = FakeRegulator()
    fake_op = FakeOperatorRegistry()
    port = FakeDronePort(valid_ports={"ONLY-THIS"})
    firmware = FirmwareService(storage)
    cert_svc = CertificationService(storage, regulator=fake_reg)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg, operator_fleet=fake_op)
    firmware.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": "fw-neg",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "x",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p",
        },
    )
    c = cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-neg")
    reg_svc.register(
        Roles.DEVELOPER,
        {
            "serial_number": "NEG-1",
            "drone_type": "t",
            "firmware_id": "fw-neg",
            "certificate_id": c["certificate_id"],
            "security_goals": ["ЦБ-1"],
            "price": 1,
        },
    )
    purchase = PurchaseService(storage, regulator=fake_reg, operator_fleet=fake_op, drone_port=port)
    out = purchase.purchase(Roles.OPERATOR, op["username"], "NEG-1", destination_droneport_id="MISSING")
    assert out["delivery_status"] == "delivery_failed"
    with storage.connect() as connection:
        row = connection.execute(
            "SELECT physical_safety_responsibility, delivery_status FROM drones WHERE serial_number='NEG-1'"
        ).fetchone()
    assert row["physical_safety_responsibility"] == "developer"
    assert row["delivery_status"] == "delivery_failed"


def test_integration_tasks_documents_droneport_contract() -> None:
    doc = Path(__file__).resolve().parents[2] / "docs" / "integration_tasks.md"
    text = doc.read_text(encoding="utf-8")
    assert "accept_delivered_drone" in text
    assert "systems/drone_port" in text
    assert "не модифицируются" in text or "не изменяются" in text


def test_regulator_rejects_goals_outside_certificate(storage: SQLiteStorage) -> None:
    _, dev, _ = _bootstrap_dev_op(storage)
    fake_reg = FakeRegulator()
    firmware = FirmwareService(storage)
    cert_svc = CertificationService(storage, regulator=fake_reg)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg)
    firmware.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": "fw-g",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "h",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p",
        },
    )
    c = cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-g")
    with pytest.raises(ValueError, match="security_goals_mismatch"):
        reg_svc.register(
            Roles.DEVELOPER,
            {
                "serial_number": "SX",
                "drone_type": "t",
                "firmware_id": "fw-g",
                "certificate_id": c["certificate_id"],
                "security_goals": ["ЦБ-2"],
                "price": 1,
            },
        )


def test_empty_drone_security_goals_allowed_and_excluded_from_mission(storage: SQLiteStorage) -> None:
    _, dev, op = _bootstrap_dev_op(storage)
    fake_reg = FakeRegulator()
    fake_op = FakeOperatorRegistry()
    firmware = FirmwareService(storage)
    cert_svc = CertificationService(storage, regulator=fake_reg)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg, operator_fleet=fake_op)
    firmware.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": "fw-e",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "h",
            "security_goals": ["ЦБ-1", "ЦБ-2"],
            "authenticity_proof": "p",
        },
    )
    c = cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-e")
    reg_svc.register(
        Roles.DEVELOPER,
        {
            "serial_number": "EMPTY-G",
            "drone_type": "t",
            "firmware_id": "fw-e",
            "certificate_id": c["certificate_id"],
            "security_goals": [],
            "price": 1,
        },
    )
    PurchaseService(storage, regulator=fake_reg, operator_fleet=fake_op).purchase(
        Roles.OPERATOR, op["username"], "EMPTY-G"
    )
    assert fake_op.select_for_mission(["ЦБ-1"]) == []


def test_fake_regulator_register_idempotency() -> None:
    reg = FakeRegulator()
    reg.certify_firmware(
        {
            "correlation_id": "c1",
            "payload": {"firmware_id": "fw", "security_goals": ["ЦБ-1"]},
        }
    )
    env = {
        "correlation_id": "same",
        "payload": {
            "serial_number": "I1",
            "firmware_id": "fw",
            "certificate_id": "cert-drone-fw",
            "security_goals": ["ЦБ-1"],
        },
    }
    a = reg.register_drone_instance(env)
    b = reg.register_drone_instance(env)
    assert a == b


def test_critical_vulnerability_revokes_certificate_and_blocks_fleet(storage: SQLiteStorage) -> None:
    _, dev, op = _bootstrap_dev_op(storage)
    fake_reg = FakeRegulator()
    fake_reg.vuln_response = {"decision": "revoke_certificate"}
    fake_op = FakeOperatorRegistry()
    journal = FakeDroneAnalytics()
    sink = _journal_sink(storage, journal)
    firmware = FirmwareService(storage)
    cert_svc = CertificationService(storage, regulator=fake_reg, security_journal=sink)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg, operator_fleet=fake_op)
    vuln = CriticalVulnerabilityService(storage, regulator=fake_reg, security_journal=sink, operator_fleet=fake_op)
    firmware.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": "fw-v",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "h",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p",
        },
    )
    cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-v")
    reg_svc.register(
        Roles.DEVELOPER,
        {
            "serial_number": "V1",
            "drone_type": "t",
            "firmware_id": "fw-v",
            "certificate_id": "cert-drone-fw-v",
            "security_goals": ["ЦБ-1"],
            "price": 1,
        },
    )
    PurchaseService(storage, regulator=fake_reg, operator_fleet=fake_op).purchase(Roles.OPERATOR, op["username"], "V1")
    vuln.report(Roles.DEVELOPER, "fw-v", "CVE-TEST", correlation_id="corr-v1")
    with storage.connect() as connection:
        st = connection.execute("SELECT registration_status FROM drones WHERE serial_number='V1'").fetchone()[0]
        cs = connection.execute("SELECT certificate_status FROM certificates WHERE firmware_id='fw-v'").fetchone()[0]
    assert st == "revoked"
    assert cs == "revoked"
    assert fake_op.drones["V1"]["registration_status"] == "revoked"
    msgs = " ".join(e.get("message", "") for e in journal.events)
    assert "critical_vulnerability_reported" in msgs
    assert "certificate_revoked" in msgs


def test_critical_vulnerability_narrows_security_goals(storage: SQLiteStorage) -> None:
    _, dev, op = _bootstrap_dev_op(storage)
    fake_reg = FakeRegulator()
    fake_reg.vuln_response = {"decision": "update_security_goals", "effective_security_goals": ["ЦБ-1"]}
    fake_op = FakeOperatorRegistry()
    firmware = FirmwareService(storage)
    cert_svc = CertificationService(storage, regulator=fake_reg)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg, operator_fleet=fake_op)
    vuln = CriticalVulnerabilityService(storage, regulator=fake_reg, operator_fleet=fake_op)
    firmware.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": "fw-n",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "h",
            "security_goals": ["ЦБ-1", "ЦБ-2"],
            "authenticity_proof": "p",
        },
    )
    cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-n")
    reg_svc.register(
        Roles.DEVELOPER,
        {
            "serial_number": "N1",
            "drone_type": "t",
            "firmware_id": "fw-n",
            "certificate_id": "cert-drone-fw-n",
            "security_goals": ["ЦБ-1", "ЦБ-2"],
            "price": 1,
        },
    )
    PurchaseService(storage, regulator=fake_reg, operator_fleet=fake_op).purchase(Roles.OPERATOR, op["username"], "N1")
    vuln.report(Roles.DEVELOPER, "fw-n", "narrow goals", correlation_id="corr-n1")
    with storage.connect() as connection:
        goals = connection.execute("SELECT security_goals FROM drones WHERE serial_number='N1'").fetchone()[0]
    from shared.storage import decode_json

    assert decode_json(goals) == ["ЦБ-1"]
    assert fake_op.drones["N1"]["security_goals"] == ["ЦБ-1"]


def test_analytics_failure_does_not_block_certify(storage: SQLiteStorage) -> None:
    _, dev, _ = _bootstrap_dev_op(storage)
    fake_reg = FakeRegulator()
    bad_journal = FakeDroneAnalytics(fail=True)
    sink = _journal_sink(storage, bad_journal)
    firmware = FirmwareService(storage)
    cert_svc = CertificationService(storage, regulator=fake_reg, security_journal=sink)
    firmware.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": "fw-a",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "h",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p",
        },
    )
    cert_svc.certify(Roles.DEVELOPER, dev["username"], "fw-a")
    with storage.connect() as connection:
        row = connection.execute("SELECT last_status FROM analytics_delivery WHERE id=1").fetchone()
    assert row["last_status"] == "failed"
