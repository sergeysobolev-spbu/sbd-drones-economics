"""Сертификация прошивки и реестр сертификатов."""

from __future__ import annotations

import time
import uuid
from typing import Any

from shared.audit_log_ipc import SupportsSecurityJournal
from shared.integration_adapters import RegulatorPort
from shared.models import Certificate, SecurityEvent
from shared.storage import SQLiteStorage, decode_json, encode_json
from shared.tcb import regulator_certify_status_ok, require_role
from shared.topics import Roles


class CertificationService:
    """Create certification requests and certificates."""

    def __init__(
        self,
        storage: SQLiteStorage,
        regulator: RegulatorPort | None = None,
        security_journal: SupportsSecurityJournal | None = None,
    ):
        self.storage = storage
        self.regulator = regulator
        self.security_journal = security_journal

    def certify(self, actor_role: str, requested_by: str, firmware_id: str) -> dict[str, Any]:
        """Certify firmware and persist a signed certificate placeholder."""
        require_role(actor_role, Roles.DEVELOPER)
        correlation_id = f"cert-{uuid.uuid4().hex[:12]}"
        with self.storage.connect() as connection:
            firmware = connection.execute(
                "SELECT * FROM firmware_versions WHERE firmware_id = ?",
                (firmware_id,),
            ).fetchone()
            if firmware is None:
                raise ValueError("firmware is not found")
            request_id = f"cert-request-{uuid.uuid4().hex[:12]}"
            certification_cost = 1000.0
            if self.regulator is not None:
                env = {
                    "schema_version": "uas-cert.v1",
                    "correlation_id": correlation_id,
                    "sender": "systems.uas_dev_company",
                    "actor": requested_by,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "payload": {
                        "firmware_id": firmware_id,
                        "supplier": firmware["supplier"],
                        "drone_type": firmware["drone_type"],
                        "version": firmware["version"],
                        "firmware_hash": firmware["firmware_hash"] or "",
                        "source_repo_url": firmware["source_repo_url"] or "",
                        "source_commit": firmware["source_commit"] or "",
                        "security_goals": decode_json(firmware["security_goals"]),
                        "authenticity_proof": firmware["authenticity_proof"],
                    },
                }
                reg_out = self.regulator.certify_firmware(env)
                status = str(reg_out.get("status", "")).lower()
                if not regulator_certify_status_ok(status):
                    reason = reg_out.get("reason_code", "certification rejected")
                    raise ValueError(str(reason))
                cert_goals = tuple(reg_out.get("security_goals") or decode_json(firmware["security_goals"]))
                certificate = Certificate(
                    certificate_id=str(reg_out.get("certificate_id") or f"cert-drone-{firmware_id}"),
                    firmware_id=firmware_id,
                    security_goals=cert_goals,
                    signed_by=str(reg_out.get("signed_by") or "systems.regulator"),
                )
            else:
                certificate = Certificate(
                    certificate_id=f"cert-drone-{firmware_id}",
                    firmware_id=firmware_id,
                    security_goals=tuple(decode_json(firmware["security_goals"])),
                    signed_by="systems.regulator",
                )
            connection.execute(
                """
                INSERT INTO certification_requests(request_id, firmware_id, requested_by, status, certification_cost)
                VALUES (?, ?, ?, 'certified', ?)
                """,
                (request_id, firmware_id, requested_by, certification_cost),
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO certificates(
                    certificate_id, firmware_id, security_goals, signed_by,
                    certificate_status, effective_security_goals
                )
                VALUES (?, ?, ?, ?, 'active', ?)
                """,
                (
                    certificate.certificate_id,
                    certificate.firmware_id,
                    encode_json(certificate.security_goals),
                    certificate.signed_by,
                    encode_json(certificate.security_goals),
                ),
            )
        if self.security_journal:
            self.security_journal.try_record(
                SecurityEvent(
                    "firmware_certified",
                    "info",
                    "certification_service",
                    certificate.certificate_id,
                    f"firmware_id={firmware_id} requested_by={requested_by}",
                )
            )
        return {
            "request_id": request_id,
            "certificate_id": certificate.certificate_id,
            "status": "certified",
            "certification_cost": certification_cost,
            "correlation_id": correlation_id,
        }

    def list_certificates(self, actor_role: str) -> list[dict[str, Any]]:
        """Return certified firmware rows with cost and a stub DVB size for the UI."""
        require_role(actor_role, Roles.DEVELOPER)
        with self.storage.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.certificate_id,
                    c.firmware_id,
                    c.security_goals,
                    c.effective_security_goals,
                    c.certificate_status,
                    c.signed_by,
                    c.created_at AS certificate_created_at,
                    f.drone_type,
                    f.version,
                    f.supplier,
                    f.firmware_hash,
                    f.source_repo_url,
                    f.source_commit,
                    f.submitted_by,
                    (
                        SELECT cr.certification_cost
                        FROM certification_requests cr
                        WHERE cr.firmware_id = c.firmware_id
                        ORDER BY cr.created_at DESC
                        LIMIT 1
                    ) AS certification_cost
                FROM certificates c
                JOIN firmware_versions f ON f.firmware_id = c.firmware_id
                ORDER BY c.created_at DESC
                """
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            goal_list = decode_json(row["security_goals"])
            eff_list = decode_json(row["effective_security_goals"])
            fh = row["firmware_hash"] or ""
            dvb_size_kb = round(32.0 + len(fh) * 0.4 + len(goal_list) * 8.0, 1)
            item = dict(row)
            item["security_goals"] = goal_list
            item["effective_security_goals"] = eff_list
            item["dvb_size_kb"] = dvb_size_kb
            result.append(item)
        return result
