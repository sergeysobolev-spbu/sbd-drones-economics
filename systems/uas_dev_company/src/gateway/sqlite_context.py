"""In-process HTTP context: все доменные сервисы напрямую (учебный режим sqlite)."""

from __future__ import annotations

import os

from analytics_adapter import AnalyticsAdapterService
from audit_log.audit_service import AuditLogService, LocalAuditJournalPort
from certification_service.certification_service import CertificationService
from drone_registry.registry_service import DroneRegistryService
from firmware_ingestion.firmware_service import FirmwareService
from purchase_service.purchase_core import PurchaseService
from shared.storage import SQLiteStorage
from user_management.user_service import UserService


def _sqlite_central_journal(storage: SQLiteStorage) -> AnalyticsAdapterService | None:
    if os.environ.get("DRONE_ANALYTICS_ENABLED", "").strip().lower() not in ("1", "true", "yes", "on"):
        return None
    return AnalyticsAdapterService(
        storage,
        True,
        url=os.environ.get("DRONE_ANALYTICS_URL", "").strip(),
        api_key=os.environ.get("DRONE_ANALYTICS_API_KEY", "").strip(),
    )


class ApiContext:
    """Container for services used by HTTP handlers (только при UAS_GATEWAY_BACKEND=sqlite)."""

    def __init__(self, storage: SQLiteStorage):
        self.storage = storage
        central = _sqlite_central_journal(storage)
        self.audit = AuditLogService(storage, central_journal=central)
        sink = LocalAuditJournalPort(self.audit)
        self.users = UserService(storage, security_journal=sink)
        self.firmware = FirmwareService(storage, security_journal=sink)
        self.certification = CertificationService(storage, security_journal=sink)
        self.registry = DroneRegistryService(storage, security_journal=sink)
        self.purchase = PurchaseService(storage, security_journal=sink)

    @property
    def jwt_secret(self) -> str:
        """Секрет подписи JWT; в dev достаточно ненулевого значения по умолчанию."""
        return os.environ.get("JWT_SECRET", "uas_dev_company_dev_jwt_change_me_in_production").strip()
