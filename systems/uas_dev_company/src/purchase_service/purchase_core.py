"""Покупка, перерегистрация и доставка в дронопорт."""

from __future__ import annotations

import time
import uuid
from typing import Any

from shared.audit_log_ipc import SupportsSecurityJournal
from shared.integration_adapters import DronePortPort, OperatorFleetPort, RegulatorPort
from shared.models import PurchaseOrder, SecurityEvent
from shared.storage import SQLiteStorage, decode_json, encode_json
from shared.tcb import (
    drone_port_response_accepted,
    regulator_reregistration_status_ok,
    require_role,
    validate_purchase_prerequisites,
)
from shared.topics import Roles


class PurchaseService:
    """Purchase certified drones from the developer registry."""

    def __init__(
        self,
        storage: SQLiteStorage,
        regulator: RegulatorPort | None = None,
        security_journal: SupportsSecurityJournal | None = None,
        operator_fleet: OperatorFleetPort | None = None,
        drone_port: DronePortPort | None = None,
    ):
        self.storage = storage
        self.regulator = regulator
        self.security_journal = security_journal
        self.operator_fleet = operator_fleet
        self.drone_port = drone_port

    def purchase(
        self,
        actor_role: str,
        operator_username: str,
        serial_number: str,
        *,
        destination_droneport_id: str = "",
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Create an authorized purchase order; при интеграции — перерегистрация и доставка в дронопорт."""
        require_role(actor_role, Roles.OPERATOR)
        order = PurchaseOrder(
            order_id=f"order-{uuid.uuid4().hex[:12]}",
            serial_number=serial_number,
            operator_username=operator_username,
        )
        dest = str(destination_droneport_id or "").strip()
        r_corr = str(correlation_id or "").strip() or f"rereg-{uuid.uuid4().hex[:12]}"

        with self.storage.connect() as connection:
            drone = connection.execute(
                """
                SELECT d.*, c.certificate_status AS cert_status
                FROM drones d
                JOIN certificates c ON c.certificate_id = d.certificate_id
                WHERE d.serial_number = ?
                """,
                (serial_number,),
            ).fetchone()
            if drone is None:
                raise ValueError("available certified drone is required")
            validate_purchase_prerequisites(
                drone_status=str(drone["status"]),
                certificate_status=str(drone["cert_status"]) if drone["cert_status"] is not None else None,
                registration_status=str(drone["registration_status"]) if drone["registration_status"] is not None else None,
                registration_id=str(drone["registration_id"]) if drone["registration_id"] is not None else None,
                regulator_integration_enabled=self.regulator is not None,
            )

        reg_out: dict[str, Any] | None = None
        if self.regulator is not None:
            with self.storage.connect() as connection:
                fw = connection.execute(
                    "SELECT * FROM firmware_versions WHERE firmware_id = ?",
                    (drone["firmware_id"],),
                ).fetchone()
            env = {
                "schema_version": "uas-registration.v1",
                "correlation_id": r_corr,
                "sender": "systems.uas_dev_company",
                "actor": operator_username,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "payload": {
                    "registration_id": drone["registration_id"],
                    "serial_number": serial_number,
                    "from_owner_id": str(fw["supplier"] if fw else "uas-dev-company"),
                    "to_owner_id": operator_username,
                    "reason": "ownership_transfer",
                    "purchase_order_id": order.order_id,
                    "certificate_id": drone["certificate_id"],
                },
            }
            reg_out = self.regulator.reregister_drone_instance(env)
            if not regulator_reregistration_status_ok(str(reg_out.get("status", ""))):
                raise ValueError(str(reg_out.get("reason_code") or "reregistration rejected"))

        new_reg_version = int((reg_out or {}).get("registration_version") or drone["registration_version"] or 1)
        payload_goals = (reg_out or {}).get("security_goals")
        updated_goals_json: str | None = None
        if payload_goals is not None:
            updated_goals_json = encode_json(list(payload_goals))

        with self.storage.connect() as connection:
            connection.execute(
                "INSERT INTO purchases(order_id, serial_number, operator_username) VALUES (?, ?, ?)",
                (order.order_id, order.serial_number, order.operator_username),
            )
            if self.regulator is None:
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

        if self.security_journal:
            self.security_journal.try_record(
                SecurityEvent(
                    "drone_purchased",
                    "notice",
                    "purchase_service",
                    order.order_id,
                    f"serial={serial_number} operator={operator_username}",
                )
            )

        if self.regulator is not None and self.operator_fleet is not None:
            sg = list(decode_json(updated_goals_json)) if updated_goals_json else list(decode_json(drone["security_goals"]))
            self.operator_fleet.import_drone_reregistered(
                {
                    "schema_version": "uas-registration-event.v1",
                    "correlation_id": r_corr,
                    "sender": "systems.regulator",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "payload": {
                        "registration_id": drone["registration_id"],
                        "registration_version": new_reg_version,
                        "serial_number": serial_number,
                        "owner_operator_id": operator_username,
                        "certificate_id": drone["certificate_id"],
                        "firmware_id": drone["firmware_id"],
                        "security_goals": sg,
                        "status": "reregistered",
                    },
                }
            )

        delivery_status = "none"
        port_reason = ""
        if self.regulator is not None and dest and self.drone_port is not None:
            port_env = {
                "schema_version": "uas-droneport-delivery.v1",
                "correlation_id": f"dlv-{uuid.uuid4().hex[:12]}",
                "sender": "systems.uas_dev_company",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "payload": {
                    "drone_id": serial_number,
                    "serial_number": serial_number,
                    "model": drone["drone_type"],
                    "port_id": dest,
                    "registration_id": drone["registration_id"],
                    "certificate_id": drone["certificate_id"],
                },
            }
            pr = self.drone_port.accept_delivered_drone(port_env)
            ok = drone_port_response_accepted(str(pr.get("status", "")))
            delivery_status = "delivered" if ok else "delivery_failed"
            port_reason = str(pr.get("reason_code") or "")
            delivered_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) if ok else ""
            phys = "operator" if ok else "developer"
            with self.storage.connect() as connection:
                connection.execute(
                    """
                    UPDATE drones SET
                        delivery_status = ?,
                        delivered_at = ?,
                        physical_safety_responsibility = ?
                    WHERE serial_number = ?
                    """,
                    (delivery_status, delivered_at, phys, serial_number),
                )
            if self.security_journal:
                if ok:
                    self.security_journal.try_record(
                        SecurityEvent(
                            "drone_delivered_to_droneport",
                            "notice",
                            "purchase_service",
                            serial_number,
                            f"port={dest}",
                        )
                    )
                    self.security_journal.try_record(
                        SecurityEvent(
                            "physical_responsibility_transferred",
                            "warning",
                            "purchase_service",
                            serial_number,
                            "to=operator",
                        )
                    )
                else:
                    self.security_journal.try_record(
                        SecurityEvent(
                            "drone_delivery_failed",
                            "error",
                            "purchase_service",
                            serial_number,
                            f"port={dest} reason={port_reason}",
                        )
                    )

        out: dict[str, Any] = {
            "order_id": order.order_id,
            "serial_number": serial_number,
            "purchased": True,
            "correlation_id": r_corr,
            "delivery_status": delivery_status,
        }
        if port_reason:
            out["delivery_reason"] = port_reason
        return out
