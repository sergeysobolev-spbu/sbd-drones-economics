"""Обработчики сообщений certification_service."""

from __future__ import annotations

from typing import Any, Callable

from certification_service.critical_vulnerability_service import CriticalVulnerabilityService
from shared.services import CertificationService
from shared.storage import SQLiteStorage
from shared.topics import Actions
from shared.worker_deps import WorkerServiceDeps


def build_certification_handlers(
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    cert = CertificationService(
        storage,
        regulator=deps.regulator,
        security_journal=deps.security_journal,
    )
    vuln = CriticalVulnerabilityService(
        storage,
        regulator=deps.regulator,
        security_journal=deps.security_journal,
        operator_fleet=deps.operator_fleet,
    )

    def certify(payload: dict[str, Any]) -> dict[str, Any]:
        return cert.certify(
            str(payload["actor_role"]),
            str(payload["requested_by"]),
            str(payload["firmware_id"]),
        )

    def list_certificates(payload: dict[str, Any]) -> dict[str, Any]:
        rows = cert.list_certificates(str(payload["actor_role"]))
        return {"certificates": rows}

    def report_critical_vulnerability(payload: dict[str, Any]) -> dict[str, Any]:
        corr = payload.get("correlation_id")
        return vuln.report(
            str(payload["actor_role"]),
            str(payload["firmware_id"]),
            str(payload.get("description") or ""),
            correlation_id=str(corr) if corr is not None else None,
            incident_type=str(payload.get("incident_type") or "critical"),
        )

    return {
        Actions.CERTIFY_FIRMWARE: certify,
        Actions.LIST_CERTIFICATES: list_certificates,
        Actions.REPORT_CRITICAL_VULNERABILITY: report_critical_vulnerability,
    }
