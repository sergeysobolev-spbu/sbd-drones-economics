"""Unit tests for UAS development company services."""

from __future__ import annotations

import sqlite3

import pytest

from shared.models import SecurityEvent
from analytics_adapter import AnalyticsAdapterService
from audit_log.audit_service import AuditLogService
from certification_service.certification_service import CertificationService
from drone_registry.registry_service import DroneRegistryService
from firmware_ingestion.firmware_service import FirmwareService
from purchase_service.purchase_core import PurchaseService
from shared.services import AuthorizationError
from user_management.user_service import UserService
from shared.storage import MONOLITH, SQLiteStorage
from shared.topics import ComponentTopics, Roles
from shared.tcb import security_event_to_analytics_payload
from shared.audit_log_ipc import make_security_journal_ipc_forwarder


@pytest.fixture()
def storage(tmp_path):
    return SQLiteStorage(MONOLITH, db_path=tmp_path / "test.sqlite3")


def test_admin_crud_and_password_hash(storage):
    users = UserService(storage)
    admin = users.bootstrap_admin("admin", "secret")
    created = users.create_user(admin["role"], "dev", Roles.DEVELOPER, "devpass")

    assert created["role"] == Roles.DEVELOPER
    assert users.authenticate("dev", "devpass")["role"] == Roles.DEVELOPER

    with storage.connect() as connection:
        row = connection.execute("SELECT password_hash FROM users WHERE username = 'dev'").fetchone()
    assert row["password_hash"] != "devpass"
    assert row["password_hash"].startswith("pbkdf2_sha256$")


def test_non_admin_cannot_create_users(storage):
    users = UserService(storage)
    users.bootstrap_admin("admin", "secret")
    users.create_user(Roles.ADMIN, "operator", Roles.OPERATOR, "pass")

    with pytest.raises(AuthorizationError):
        users.create_user(Roles.OPERATOR, "dev", Roles.DEVELOPER, "pass")


def test_admin_blocks_user_and_cannot_block_last_admin(storage):
    users = UserService(storage)
    users.bootstrap_admin("admin", "secret")
    users.create_user(Roles.ADMIN, "dev", Roles.DEVELOPER, "pass")
    users.set_user_active(Roles.ADMIN, "dev", False)
    with pytest.raises(AuthorizationError):
        users.authenticate("dev", "pass")
    users.set_user_active(Roles.ADMIN, "dev", True)
    assert users.authenticate("dev", "pass")["role"] == Roles.DEVELOPER
    with pytest.raises(ValueError, match="last administrator"):
        users.set_user_active(Roles.ADMIN, "admin", False)


def test_certify_returns_cost_and_list_certificates(storage):
    users = UserService(storage)
    users.bootstrap_admin("admin", "secret")
    users.create_user(Roles.ADMIN, "dev", Roles.DEVELOPER, "pass")
    firmware = FirmwareService(storage)
    firmware.submit(
        Roles.DEVELOPER,
        "dev",
        {
            "firmware_id": "fw-x",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "h",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p",
        },
    )
    cert_svc = CertificationService(storage)
    out = cert_svc.certify(Roles.DEVELOPER, "dev", "fw-x")
    assert out["certification_cost"] == 1000.0
    listed = cert_svc.list_certificates(Roles.DEVELOPER)
    assert len(listed) == 1
    assert listed[0]["certificate_id"] == out["certificate_id"]
    assert listed[0]["dvb_size_kb"] > 0


def test_list_registered_drones_role(storage):
    users = UserService(storage)
    users.bootstrap_admin("admin", "secret")
    users.create_user(Roles.ADMIN, "dev", Roles.DEVELOPER, "pass")
    users.create_user(Roles.ADMIN, "op", Roles.OPERATOR, "pass")
    firmware = FirmwareService(storage)
    firmware.submit(
        Roles.DEVELOPER,
        "dev",
        {
            "firmware_id": "fw-d",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "hh",
            "security_goals": ["ЦБ-2"],
            "authenticity_proof": "p",
        },
    )
    cert_svc = CertificationService(storage)
    c = cert_svc.certify(Roles.DEVELOPER, "dev", "fw-d")
    reg = DroneRegistryService(storage)
    reg.register(
        Roles.DEVELOPER,
        {
            "serial_number": "SN-1",
            "drone_type": "t",
            "firmware_id": "fw-d",
            "certificate_id": c["certificate_id"],
            "security_goals": ["ЦБ-2"],
            "price": 1,
        },
    )
    dev_list = reg.list_registered(Roles.DEVELOPER)
    op_list = reg.list_registered(Roles.OPERATOR)
    assert len(dev_list) == 1 and dev_list[0]["serial_number"] == "SN-1"
    assert len(op_list) == 1
    with pytest.raises(AuthorizationError):
        reg.list_registered(Roles.ADMIN)


def test_certified_drone_purchase_flow_persists(storage):
    users = UserService(storage)
    users.bootstrap_admin("admin", "secret")
    users.create_user(Roles.ADMIN, "dev", Roles.DEVELOPER, "pass")
    users.create_user(Roles.ADMIN, "operator", Roles.OPERATOR, "pass")

    firmware = FirmwareService(storage)
    submitted = firmware.submit(
        Roles.DEVELOPER,
        "dev",
        {
            "firmware_id": "fw-1",
            "supplier": "agrodron-team",
            "drone_type": "agro",
            "version": "1.0.0",
            "firmware_hash": "abc123",
            "security_goals": ["ЦБ-1", "ЦБ-3"],
            "authenticity_proof": "signed",
        },
    )
    assert submitted["accepted"] is True

    certification = CertificationService(storage)
    cert = certification.certify(Roles.DEVELOPER, "dev", "fw-1")

    registry = DroneRegistryService(storage)
    registry.register(
        Roles.DEVELOPER,
        {
            "serial_number": "DRONE-1",
            "drone_type": "agro",
            "firmware_id": "fw-1",
            "certificate_id": cert["certificate_id"],
            "security_goals": ["ЦБ-1", "ЦБ-3"],
            "price": 12000,
        },
    )

    purchase = PurchaseService(storage, registry=registry)
    order = purchase.purchase(Roles.OPERATOR, "operator", "DRONE-1")
    assert order["purchased"] is True

    with storage.connect() as connection:
        drone = connection.execute("SELECT status FROM drones WHERE serial_number = 'DRONE-1'").fetchone()
        persisted_order = connection.execute("SELECT order_id FROM purchases").fetchone()
    assert drone["status"] == "sold"
    assert persisted_order["order_id"] == order["order_id"]


def test_uncertified_drone_registration_is_rejected(storage):
    registry = DroneRegistryService(storage)
    with pytest.raises(ValueError):
        registry.register(
            Roles.DEVELOPER,
            {
                "serial_number": "DRONE-2",
                "drone_type": "agro",
                "firmware_id": "missing",
                "certificate_id": "missing",
                "security_goals": ["ЦБ-1"],
                "price": 10,
            },
        )


def test_drone_register_rejects_goal_outside_certificate(storage):
    users = UserService(storage)
    users.bootstrap_admin("admin", "secret")
    users.create_user(Roles.ADMIN, "dev", Roles.DEVELOPER, "pass")
    firmware = FirmwareService(storage)
    firmware.submit(
        Roles.DEVELOPER,
        "dev",
        {
            "firmware_id": "fw-g",
            "supplier": "s",
            "drone_type": "t",
            "version": "1",
            "firmware_hash": "hh",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p",
        },
    )
    cert_svc = CertificationService(storage)
    c = cert_svc.certify(Roles.DEVELOPER, "dev", "fw-g")
    reg = DroneRegistryService(storage)
    with pytest.raises(ValueError, match="unknown security goal"):
        reg.register(
            Roles.DEVELOPER,
            {
                "serial_number": "SX",
                "drone_type": "t",
                "firmware_id": "fw-g",
                "certificate_id": c["certificate_id"],
                "security_goals": ["ЦБ-99"],
                "price": 1,
            },
        )


def test_firmware_submit_source_repo_without_hash(storage):
    users = UserService(storage)
    users.bootstrap_admin("admin", "secret")
    users.create_user(Roles.ADMIN, "dev", Roles.DEVELOPER, "pass")
    firmware = FirmwareService(storage)
    firmware.submit(
        Roles.DEVELOPER,
        "dev",
        {
            "firmware_id": "fw-git",
            "supplier": "s",
            "drone_type": "t",
            "version": "main",
            "firmware_hash": "",
            "source_repo_url": "https://gitlab.example/repo.git",
            "source_commit": "deadbeef",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "repo-submit",
        },
    )
    with storage.connect() as connection:
        row = connection.execute("SELECT firmware_id, firmware_hash FROM firmware_versions WHERE firmware_id = 'fw-git'").fetchone()
    assert row["firmware_id"] == "fw-git"


def test_analytics_disabled_does_not_fail_core_operation(storage):
    analytics = AnalyticsAdapterService(storage, enabled=False, url="")
    result = analytics.send({"event": "purchase"})

    assert result["status"] == "disabled"
    assert result["delivered"] is False


def test_audit_log_records_security_events(storage):
    audit = AuditLogService(storage)
    audit.log(SecurityEvent("login_denied", "warning", "api_gateway", "unknown"))
    assert audit.list_events()[0]["event_type"] == "login_denied"


class _CaptureEmit:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def try_emit(self, event: dict) -> None:
        self.payloads.append(event)


def test_audit_log_forwards_to_central_journal_when_configured(storage):
    cap = _CaptureEmit()
    audit = AuditLogService(storage, central_journal=cap)
    ev = SecurityEvent("gate_evt", "info", "api_gateway", "/api/x", "detail")
    audit.log(ev)
    assert cap.payloads
    assert "gate_evt" in cap.payloads[0].get("message", "")
    assert cap.payloads[0].get("service") == "infopanel"


def test_security_event_to_analytics_payload_shape() -> None:
    ev = SecurityEvent("t1", "warning", "user_management", "sub", "d")
    payload = security_event_to_analytics_payload(ev, instance_id_override="inst-a")
    assert payload["severity"] == "warning"
    assert payload["service"] == "operator"
    assert 1 <= int(payload["service_id"]) <= 32767
    assert "t1" in payload["message"] and "sub" in payload["message"]
    assert "ts_utc=" in payload["message"] and "instance_id=inst-a" in payload["message"]


def test_make_security_journal_ipc_disabled_for_audit_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UAS_SECURITY_JOURNAL_IPC", "true")
    from broker.system_bus import SystemBus

    class _Bus(SystemBus):
        def publish(self, topic, message):
            return True

        def subscribe(self, topic, callback):
            return True

        def unsubscribe(self, topic):
            return True

        def request(self, topic, message, timeout=30.0):
            return {}

        def request_async(self, topic, message, timeout=30.0):
            raise NotImplementedError

        def start(self):
            return None

        def stop(self):
            return None

    assert make_security_journal_ipc_forwarder(_Bus(), ComponentTopics.AUDIT_LOG) is None
    assert make_security_journal_ipc_forwarder(_Bus(), ComponentTopics.ANALYTICS_ADAPTER) is None
