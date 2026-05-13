"""Реестр дронов и регистрация у Регулятора."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from typing import Any

from shared.audit_log_ipc import SupportsSecurityJournal
from shared.integration_adapters import OperatorFleetPort, RegulatorPort
from shared.models import DroneRegistryRecord, SecurityEvent, normalize_drone_goals
from shared.storage import SQLiteStorage, decode_json, encode_json
from shared.tcb import (
    assert_drone_goals_subset_when_local_regulator,
    apply_effective_goals_to_drone_goals,
    regulator_register_status_ok,
    require_developer_or_operator_for_registry,
    require_role,
)
from shared.tcb.cb_constants import normalize_canonical_security_goals
from shared.topics import Roles

CertSnapshotFn = Callable[[str, str], dict[str, Any] | None]
FirmwareRowFn = Callable[[str], dict[str, Any] | None]


class DroneRegistryService:
    """Register drones with certified firmware."""

    def __init__(
        self,
        storage: SQLiteStorage,
        regulator: RegulatorPort | None = None,
        security_journal: SupportsSecurityJournal | None = None,
        operator_fleet: OperatorFleetPort | None = None,
        certificate_snapshot: CertSnapshotFn | None = None,
        firmware_row: FirmwareRowFn | None = None,
    ):
        self.storage = storage
        self.regulator = regulator
        self.security_journal = security_journal
        self.operator_fleet = operator_fleet
        self._certificate_snapshot = certificate_snapshot
        self._firmware_row = firmware_row

    def _cert(self, certificate_id: str, firmware_id: str) -> dict[str, Any] | None:
        if self._certificate_snapshot is not None:
            return self._certificate_snapshot(certificate_id, firmware_id)
        with self.storage.connect() as connection:
            row = connection.execute(
                "SELECT * FROM certificates WHERE certificate_id = ? AND firmware_id = ?",
                (certificate_id, firmware_id),
            ).fetchone()
            if row is None:
                return None
            r = dict(row)
            cost_row = connection.execute(
                """
                SELECT certification_cost FROM certification_requests
                WHERE firmware_id = ? ORDER BY created_at DESC LIMIT 1
                """,
                (firmware_id,),
            ).fetchone()
            r["certification_cost"] = float(cost_row["certification_cost"]) if cost_row else 0.0
            return r

    def _firmware(self, firmware_id: str) -> dict[str, Any] | None:
        if self._firmware_row is not None:
            return self._firmware_row(firmware_id)
        with self.storage.connect() as connection:
            row = connection.execute(
                "SELECT * FROM firmware_versions WHERE firmware_id = ?",
                (firmware_id,),
            ).fetchone()
            return dict(row) if row else None

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

        certificate = self._cert(certificate_id_in, firmware_id_in)
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

        fw = self._firmware(firmware_id_in)
        if fw is None:
            raise ValueError("firmware is not found for registration")

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

        cert_status = str(certificate.get("certificate_status") or "active")
        cert_eff = encode_json(decode_json(certificate["effective_security_goals"]))
        cert_sg = encode_json(decode_json(certificate["security_goals"]))
        cert_cost = float(certificate.get("certification_cost") or 0)
        with self.storage.connect() as connection:
            connection.execute(
                """
                INSERT INTO drones(
                    serial_number, drone_type, firmware_id, certificate_id, security_goals,
                    price, status, registration_id, registration_status, registration_version,
                    regulator_reason, last_regulator_correlation_id, hardware_config,
                    certificate_status, certificate_effective_security_goals,
                    certificate_security_goals, firmware_supplier, firmware_hash,
                    firmware_security_goals, certification_cost
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    cert_status,
                    cert_eff,
                    cert_sg,
                    str(fw.get("supplier") or ""),
                    str(fw.get("firmware_hash") or ""),
                    str(fw.get("security_goals") or "[]"),
                    cert_cost,
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
                SELECT * FROM drones
                WHERE status = 'available'
                  AND registration_status = 'registered_by_regulator'
                  AND IFNULL(certificate_status, 'active') = 'active'
                ORDER BY serial_number
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def list_registered(self, actor_role: str) -> list[dict[str, Any]]:
        """Все записи реестра дронов для разработчика или эксплуатанта."""
        require_developer_or_operator_for_registry(actor_role)
        with self.storage.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM drones ORDER BY serial_number",
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            goals_fw = decode_json(item["firmware_security_goals"])
            goals_cert = decode_json(item["certificate_security_goals"])
            goals_eff = decode_json(item["certificate_effective_security_goals"])
            raw_drone_sg = item.pop("security_goals")
            drone_goals = decode_json(raw_drone_sg) if isinstance(raw_drone_sg, str) else list(raw_drone_sg)
            fh = str(item.get("firmware_hash") or "")
            item["security_goals"] = drone_goals
            item["firmware_security_goals"] = goals_fw
            item["certificate_security_goals"] = goals_cert
            item["certificate_effective_security_goals"] = goals_eff
            item["dvb_size_kb"] = round(48.0 + len(fh) * 0.3 + len(drone_goals) * 6.0, 1)
            result.append(item)
        return result

    def get_drone_purchase_row(self, serial_number: str) -> dict[str, Any] | None:
        """Строка дрона для purchase_service (без JOIN)."""
        with self.storage.connect() as connection:
            row = connection.execute(
                "SELECT * FROM drones WHERE serial_number = ?",
                (serial_number,),
            ).fetchone()
            return dict(row) if row else None

    def apply_firmware_cert_decision(self, firmware_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        """Применить решение Регулятора по прошивке к дронам в реестре (междоменный вызов)."""
        dec = str(decision.get("decision") or "")
        if dec == "revoke_certificate":
            with self.storage.connect() as connection:
                connection.execute(
                    """
                    UPDATE drones SET registration_status = 'revoked', certificate_status = 'revoked'
                    WHERE firmware_id = ?
                    """,
                    (firmware_id,),
                )
            return {"updated": True}
        if dec == "update_security_goals":
            goals = decision.get("effective_security_goals")
            if not goals:
                return {"updated": False}
            norm = normalize_canonical_security_goals(goals, allow_empty=True)
            eff = encode_json(list(norm))
            with self.storage.connect() as connection:
                rows = connection.execute(
                    "SELECT serial_number, security_goals FROM drones WHERE firmware_id = ?",
                    (firmware_id,),
                ).fetchall()
                for row in rows:
                    inter = apply_effective_goals_to_drone_goals(decode_json(row["security_goals"]), list(norm))
                    connection.execute(
                        """
                        UPDATE drones SET
                            security_goals = ?,
                            certificate_effective_security_goals = ?
                        WHERE serial_number = ?
                        """,
                        (encode_json(list(inter)), eff, row["serial_number"]),
                    )
            return {"updated": True}
        return {"updated": False}

    def update_drone_after_purchase(
        self,
        serial_number: str,
        *,
        operator_username: str,
        dest: str,
        r_corr: str,
        regulator_mode: bool,
        new_reg_version: int,
        updated_goals_json: str | None,
    ) -> None:
        """Обновить запись дрона после успешной покупки (атомарно в БД реестра)."""
        with self.storage.connect() as connection:
            if not regulator_mode:
                connection.execute(
                    """
                    UPDATE drones SET
                        status = 'sold',
                        owner_operator_id = ?,
                        destination_droneport_id = ?,
                        last_regulator_correlation_id = ?
                    WHERE serial_number = ?
                    """,
                    (operator_username, dest, r_corr, serial_number),
                )
            else:
                connection.execute(
                    """
                    UPDATE drones SET
                        status = 'sold_reregistered',
                        owner_operator_id = ?,
                        destination_droneport_id = ?,
                        registration_version = ?,
                        last_regulator_correlation_id = ?,
                        delivery_status = ?,
                        physical_safety_responsibility = 'developer',
                        security_goals = COALESCE(?, security_goals)
                    WHERE serial_number = ?
                    """,
                    (
                        operator_username,
                        dest,
                        new_reg_version,
                        r_corr,
                        "pending_delivery" if dest else "none",
                        updated_goals_json,
                        serial_number,
                    ),
                )

    def update_drone_delivery(
        self,
        serial_number: str,
        *,
        delivery_status: str,
        delivered_at: str,
        physical_safety_responsibility: str,
    ) -> None:
        with self.storage.connect() as connection:
            connection.execute(
                """
                UPDATE drones SET
                    delivery_status = ?,
                    delivered_at = ?,
                    physical_safety_responsibility = ?
                WHERE serial_number = ?
                """,
                (delivery_status, delivered_at, physical_safety_responsibility, serial_number),
            )
