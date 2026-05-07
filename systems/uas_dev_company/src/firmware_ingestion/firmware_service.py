"""Приём метаданных прошивки (ЦБ-1)."""

from __future__ import annotations

import uuid
from typing import Any

from shared.audit_log_ipc import SupportsSecurityJournal
from shared.models import FirmwareVersion, SecurityEvent, normalize_goals
from shared.storage import SQLiteStorage, encode_json
from shared.tcb import require_role
from shared.topics import Roles


class FirmwareService:
    """Accept and validate firmware metadata."""

    def __init__(self, storage: SQLiteStorage, security_journal: SupportsSecurityJournal | None = None):
        self.storage = storage
        self.security_journal = security_journal

    def submit(self, actor_role: str, submitted_by: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit authentic firmware for certification."""
        require_role(actor_role, Roles.DEVELOPER)
        firmware = FirmwareVersion(
            firmware_id=payload.get("firmware_id") or f"fw-{uuid.uuid4().hex[:12]}",
            supplier=payload.get("supplier", ""),
            drone_type=payload.get("drone_type", ""),
            version=payload.get("version", ""),
            firmware_hash=str(payload.get("firmware_hash", "") or "").strip(),
            source_repo_url=str(payload.get("source_repo_url", "") or "").strip(),
            source_commit=str(payload.get("source_commit", "") or "").strip(),
            security_goals=normalize_goals(payload.get("security_goals", [])),
            authenticity_proof=str(payload.get("authenticity_proof", "") or "").strip(),
        )
        with self.storage.connect() as connection:
            connection.execute(
                """
                INSERT INTO firmware_versions(
                    firmware_id, supplier, drone_type, version, firmware_hash,
                    source_repo_url, source_commit,
                    security_goals, authenticity_proof, submitted_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    firmware.firmware_id,
                    firmware.supplier,
                    firmware.drone_type,
                    firmware.version,
                    firmware.firmware_hash or "",
                    firmware.source_repo_url,
                    firmware.source_commit,
                    encode_json(firmware.security_goals),
                    firmware.authenticity_proof,
                    submitted_by,
                ),
            )
        if self.security_journal:
            self.security_journal.try_record(
                SecurityEvent(
                    "firmware_submitted",
                    "info",
                    "firmware_ingestion",
                    firmware.firmware_id,
                    f"submitted_by={submitted_by}",
                )
            )
        return {"firmware_id": firmware.firmware_id, "accepted": True}
