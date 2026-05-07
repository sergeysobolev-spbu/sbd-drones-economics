"""Integration tests for the first UAS developer company scenario."""

from __future__ import annotations

from shared.services import (
    CertificationService,
    DroneRegistryService,
    FirmwareService,
    PurchaseService,
    UserService,
)
from shared.storage import SQLiteStorage
from shared.topics import Roles


def test_admin_developer_operator_end_to_end(tmp_path):
    storage = SQLiteStorage(tmp_path / "e2e.sqlite3")
    users = UserService(storage)
    firmware = FirmwareService(storage)
    certification = CertificationService(storage)
    registry = DroneRegistryService(storage)
    purchases = PurchaseService(storage)

    admin = users.bootstrap_admin("admin", "admin-pass")
    dev = users.create_user(admin["role"], "dev", Roles.DEVELOPER, "dev-pass")
    operator = users.create_user(admin["role"], "operator", Roles.OPERATOR, "operator-pass")

    firmware.submit(
        dev["role"],
        dev["username"],
        {
            "firmware_id": "fw-e2e",
            "supplier": "deliverydron-team",
            "drone_type": "delivery",
            "version": "2026.1",
            "firmware_hash": "sha256:e2e",
            "security_goals": ["ЦБ-1", "ЦБ-2", "ЦБ-3"],
            "authenticity_proof": "contractor-signature",
        },
    )
    certificate = certification.certify(dev["role"], dev["username"], "fw-e2e")
    registry.register(
        dev["role"],
        {
            "serial_number": "DELIVERY-001",
            "drone_type": "delivery",
            "firmware_id": "fw-e2e",
            "certificate_id": certificate["certificate_id"],
            "security_goals": ["ЦБ-1", "ЦБ-3"],
            "price": 45000,
        },
    )
    order = purchases.purchase(operator["role"], operator["username"], "DELIVERY-001")

    assert order["purchased"] is True
    assert registry.list_available() == []

    reloaded_storage = SQLiteStorage(tmp_path / "e2e.sqlite3")
    with reloaded_storage.connect() as connection:
        assert connection.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] == 3
        assert connection.execute("SELECT COUNT(*) AS c FROM certificates").fetchone()["c"] == 1
        assert connection.execute("SELECT status FROM drones WHERE serial_number = 'DELIVERY-001'").fetchone()["status"] == "sold"
