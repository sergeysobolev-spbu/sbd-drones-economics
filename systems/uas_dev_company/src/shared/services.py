"""Тонкий фасад доменных сервисов (совместимость импортов `shared.services`)."""

from __future__ import annotations

from analytics_adapter import AnalyticsAdapterService
from analytics_adapter.protocol import SupportsAnalyticsEmit
from audit_log.audit_service import AuditLogService
from certification_service.certification_service import CertificationService
from certification_service.critical_vulnerability_service import CriticalVulnerabilityService
from drone_registry.registry_service import DroneRegistryService
from firmware_ingestion.firmware_service import FirmwareService
from purchase_service.purchase_core import PurchaseService
from shared.tcb import AuthorizationError
from user_management.user_service import UserService

__all__ = [
    "AnalyticsAdapterService",
    "AuditLogService",
    "AuthorizationError",
    "CertificationService",
    "CriticalVulnerabilityService",
    "DroneRegistryService",
    "FirmwareService",
    "PurchaseService",
    "SupportsAnalyticsEmit",
    "UserService",
]
