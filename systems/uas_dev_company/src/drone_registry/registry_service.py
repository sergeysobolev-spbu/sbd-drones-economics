"""Реестр дронов и регистрация у Регулятора."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from shared.audit_log_ipc import SupportsSecurityJournal
from shared.integration_adapters import OperatorFleetPort, RegulatorPort
from shared.models import DroneRegistryRecord, SecurityEvent, normalize_drone_goals
from shared.storage import SQLiteStorage, decode_json, encode_json
from shared.tcb import (
    assert_drone_goals_subset_when_local_regulator,
    regulator_register_status_ok,
    require_developer_or_operator_for_registry,
    require_role,
)
from shared.topics import Roles


class DroneRegistryService:
    """Register drones with certified firmware."""

    def __init__(
        self,
        storage: SQLiteStorage,
        regulator: RegulatorPort | None = None,
        security_journal: SupportsSecurityJournal | None = None,
        operator_fleet: OperatorFleetPort | None = None,
    ):
        self.storage = storage
        self.regulator = regulator
        self.security_journal = security_journal
        self.operator_fleet = operator_fleet

    def register(self, actor_role: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Register a new drone after certificate validation."""
        require_role(actor_role, Roles.DEVELOPER)
        certificate_id_in = str(payload.get("certificate_id", "")).strip()
        firmware_id_in = str(payload.get("firmware_id", "")).strip()
        serial = str(payload.get("serial_number", "")).strip()
        drone_type = str(payload.get("drone_type", "")).strip()
        chosen_goals = normalize_drone_goals(payload.get("security_goals", []))
        correlation_id = str(payload.get("correlation_id") or "").strip() or f"reg-{uuid.uuid4().hex[:12]}"
        raw_hw = payload.get("hardware_config")
        if raw_hw is None:
            hw_obj: Any = {}
        elif isinstance(raw_hw, str):
            try:
                hw_obj = decode_json(raw_hw) if raw_hw.strip() else {}
            except json.JSONDecodeError:
                hw_obj = {}
        else:
            hw_obj = raw_hw
        hw_json = encode_json(hw_obj)

        with self.storage.connect() as connection:
            certificate = connection.execute(
                "SELECT * FROM certificates WHERE certificate_id = ? AND firmware_id = ?",
                (certificate_id_in, firmware_id_in),
            ).fetchone()
            if certificate is None:
                if self.security_journal:
                    self.security_journal.try_record(
                        SecurityEvent(
                            "drone_registration_failed",
                            "error",
                            "drone_registry",
                            serial or certificate_id_in or firmware_id_in,
                            f"reason=no_matching_certificate certificate_id={certificate_id_in} "
                            f"firmware_id={firmware_id_in} correlation_id={correlation_id}",
                        )
                    )
                raise ValueError("certified firmware is required")
            if str(certificate["certificate_status"] or "active") == "revoked":
                if self.security_journal:
                    self.security_journal.try_record(
                        SecurityEvent(
                            "drone_registration_failed",
                            "error",
                            "drone_registry",
                            serial,
                            f"reason=certificate_revoked certificate_id={certificate_id_in} "
                            f"firmware_id={firmware_id_in} correlation_id={correlation_id}",
                        )
                    )
                raise ValueError("certificate revoked")
            effective_goals = decode_json(certificate["effective_security_goals"])
            try:
                assert_drone_goals_subset_when_local_regulator(
                    chosen_goals=chosen_goals,
                    effective_certificate_goals=list(effective_goals),
                    regulator_integration_enabled=self.regulator is not None,
                )
            except ValueError as exc:
                if self.security_journal:
                    self.security_journal.try_record(
                        SecurityEvent(
                            "drone_registration_failed",
                            "error",
                            "drone_registry",
                            serial,
                            f"reason={exc!s} correlation_id={correlation_id}",
                        )
                    )
                raise
            record = DroneRegistryRecord(
                serial_number=serial,
                drone_type=drone_type,
                firmware_id=firmware_id_in,
                certificate_id=certificate_id_in,
                security_goals=chosen_goals,
                price=float(payload.get("price", 0)),
            )
            registration_id = ""
            registration_version = 0
            registration_status = "pending_regulator"
            regulator_reason = ""

            if self.regulator is not None:
                env = {
                    "schema_version": "uas-registration.v1",
                    "correlation_id": correlation_id,
                    "sender": "systems.uas_dev_company",
                    "actor": str(payload.get("actor") or "").strip() or "uas-developer",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "payload": {
                        "serial_number": serial,
                        "drone_type": drone_type,
                        "manufacturer_id": str(payload.get("manufacturer_id") or "uas-dev-company"),
                        "seller_id": str(payload.get("seller_id") or "uas-dev-company"),
                        "owner_operator_id": payload.get("owner_operator_id"),
                        "firmware_id": firmware_id_in,
                        "certificate_id": certificate_id_in,
                        "security_goals": list(chosen_goals),
                        "hardware_config": hw_obj,
                        "declared_price": record.price,
                    },
                }
                reg_out = self.regulator.register_drone_instance(env)
                status = str(reg_out.get("status", "")).lower()
                if not regulator_register_status_ok(status):
                    registration_status = "registration_rejected"
                    regulator_reason = str(reg_out.get("reason_code") or "registration rejected")
                    if self.security_journal:
                        self.security_journal.try_record(
                            SecurityEvent(
                                "drone_registration_failed",
                                "error",
                                "drone_registry",
                                serial,
                                f"reason=regulator_rejected {regulator_reason} correlation_id={correlation_id} "
                                f"firmware_id={firmware_id_in} certificate_id={certificate_id_in}",
                            )
                        )
                    raise ValueError(regulator_reason)
                registration_id = str(reg_out["registration_id"])
                registration_version = int(reg_out.get("registration_version") or 1)
                registration_status = "registered_by_regulator"
            else:
                registration_id = f"local-{serial}"
                registration_version = 1
                registration_status = "registered_by_regulator"

            connection.execute(
                """
                INSERT INTO drones(
                    serial_number, drone_type, firmware_id, certificate_id, security_goals,
                    price, status, registration_id, registration_status, registration_version,
                    regulator_reason, last_regulator_correlation_id, hardware_config
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.serial_number,
                    record.drone_type,
                    record.firmware_id,
                    record.certificate_id,
                    encode_json(record.security_goals),
                    record.price,
                    record.status,
                    registration_id,
                    registration_status,
                    registration_version,
                    regulator_reason,
                    correlation_id,
                    hw_json,
                ),
            )
        if self.security_journal:
            self.security_journal.try_record(
                SecurityEvent(
                    "drone_registered",
                    "info",
                    "drone_registry",
                    serial,
                    f"registration_id={registration_id} firmware_id={firmware_id_in} certificate_id={certificate_id_in}",
                )
            )
        return {
            "serial_number": record.serial_number,
            "registered": True,
            "registration_id": registration_id,
            "registration_status": registration_status,
            "correlation_id": correlation_id,
        }

    def list_available(self) -> list[dict[str, Any]]:
        """Return certified drones available for purchase."""
        with self.storage.connect() as connection:
            rows = connection.execute(
                """
                SELECT d.* FROM drones d
                JOIN certificates c ON c.certificate_id = d.certificate_id
                WHERE d.status = 'available'
                  AND d.registration_status = 'registered_by_regulator'
                  AND IFNULL(c.certificate_status, 'active') = 'active'
                ORDER BY d.serial_number
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_registered(self, actor_role: str) -> list[dict[str, Any]]:
        """Все записи реестра дронов для разработчика или эксплуатанта."""
        require_developer_or_operator_for_registry(actor_role)
        with self.storage.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    d.*,
                    fv.security_goals AS firmware_security_goals,
                    fv.firmware_hash AS firmware_hash,
                    cert.security_goals AS certificate_security_goals,
                    cert.effective_security_goals AS certificate_effective_security_goals,
                    cert.certificate_status AS certificate_status,
                    (
                        SELECT cr.certification_cost
                        FROM certification_requests cr
                        WHERE cr.firmware_id = d.firmware_id
                        ORDER BY cr.created_at DESC
                        LIMIT 1
                    ) AS certification_cost
                FROM drones d
                JOIN firmware_versions fv ON fv.firmware_id = d.firmware_id
                JOIN certificates cert ON cert.certificate_id = d.certificate_id
                ORDER BY d.serial_number
                """
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            goals_fw = decode_json(item.pop("firmware_security_goals"))
            goals_cert = decode_json(item.pop("certificate_security_goals"))
            goals_eff = decode_json(item.pop("certificate_effective_security_goals"))
            raw_drone_sg = item.pop("security_goals")
            drone_goals = decode_json(raw_drone_sg) if isinstance(raw_drone_sg, str) else list(raw_drone_sg)
            fh = str(item.pop("firmware_hash") or "")
            item["security_goals"] = drone_goals
            item["firmware_security_goals"] = goals_fw
            item["certificate_security_goals"] = goals_cert
            item["certificate_effective_security_goals"] = goals_eff
            item["dvb_size_kb"] = round(48.0 + len(fh) * 0.3 + len(drone_goals) * 6.0, 1)
            result.append(item)
        return result
