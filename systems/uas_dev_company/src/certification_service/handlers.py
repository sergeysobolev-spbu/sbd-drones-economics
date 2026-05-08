"""Обработчики сообщений certification_service."""

from __future__ import annotations

from typing import Any, Callable

from certification_service.critical_vulnerability_service import CriticalVulnerabilityService
from certification_service.certification_service import CertificationService
from shared.storage import SQLiteStorage
from shared.topics import Actions, ComponentTopics
from shared.worker_deps import WorkerServiceDeps


def build_certification_handlers(
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    assert deps.monitor_proxy_call is not None

    def _firmware_row(fid: str):
        r = deps.monitor_proxy_call(
            ComponentTopics.FIRMWARE_INGESTION,
            Actions.GET_FIRMWARE_ROW,
            {"firmware_id": fid},
        )
        return r.get("row")

    def _registry_apply(fw_id: str, decision: dict[str, Any]) -> None:
        deps.monitor_proxy_call(
            ComponentTopics.DRONE_REGISTRY,
            Actions.APPLY_FIRMWARE_CERT_DECISION,
            {"firmware_id": fw_id, "decision": decision},
        )

    cert = CertificationService(
        storage,
        regulator=deps.regulator,
        security_journal=deps.security_journal,
        firmware_row_fetch=_firmware_row,
    )
    vuln = CriticalVulnerabilityService(
        storage,
        regulator=deps.regulator,
        security_journal=deps.security_journal,
        operator_fleet=deps.operator_fleet,
        registry_apply=_registry_apply,
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

    def get_certificate_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
        snap = cert.get_certificate_snapshot(
            str(payload.get("certificate_id") or ""),
            str(payload.get("firmware_id") or ""),
        )
        return {"snapshot": snap}

    return {
        Actions.CERTIFY_FIRMWARE: certify,
        Actions.LIST_CERTIFICATES: list_certificates,
        Actions.REPORT_CRITICAL_VULNERABILITY: report_critical_vulnerability,
        Actions.GET_CERTIFICATE_SNAPSHOT: get_certificate_snapshot,
    }
