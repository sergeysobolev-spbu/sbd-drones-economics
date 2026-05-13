"""In-process HTTP context: отдельный SQLite-файл на домен (Задача 22)."""

from __future__ import annotations

import os
from pathlib import Path

from analytics_adapter import AnalyticsAdapterService
from audit_log.audit_service import AuditLogService, LocalAuditJournalPort
from certification_service.certification_service import CertificationService
from drone_registry.registry_service import DroneRegistryService
from firmware_ingestion.firmware_service import FirmwareService
from purchase_service.purchase_core import PurchaseService
from shared import domain_storage as dom
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
    """HTTP handlers: каждый домен — свой файл под UAS_DOMAIN_DATA_ROOT (или monolith по UAS_SQLITE_MONOLITH_PATH)."""

    def __init__(self, data_root: Path | str | None = None) -> None:
        monopath = os.environ.get("UAS_SQLITE_MONOLITH_PATH", "").strip()
        if monopath:
            from shared.storage import MONOLITH

            st = SQLiteStorage(MONOLITH, db_path=monopath)
            self.storage = st
            central = _sqlite_central_journal(st)
            self.audit = AuditLogService(st, central_journal=central)
            sink = LocalAuditJournalPort(self.audit)
            self.users = UserService(st, security_journal=sink)
            self.firmware = FirmwareService(st, security_journal=sink)
            self.certification = CertificationService(st, security_journal=sink)
            self.registry = DroneRegistryService(st, security_journal=sink)
            self.purchase = PurchaseService(st, security_journal=sink, registry=self.registry)
            return

        root = Path(data_root or os.environ.get("UAS_DOMAIN_DATA_ROOT", "resources/domains"))
        os.environ.setdefault("UAS_DOMAIN_DATA_ROOT", str(root.resolve()))

        st_audit = SQLiteStorage(dom.AUDIT_LOG)
        st_users = SQLiteStorage(dom.USER_MANAGEMENT)
        st_fw = SQLiteStorage(dom.FIRMWARE_INGESTION)
        st_cert = SQLiteStorage(dom.CERTIFICATION_SERVICE)
        st_reg = SQLiteStorage(dom.DRONE_REGISTRY)
        st_pur = SQLiteStorage(dom.PURCHASE_SERVICE)
        st_an = SQLiteStorage(dom.ANALYTICS_ADAPTER)

        central = _sqlite_central_journal(st_an)
        self.audit = AuditLogService(st_audit, central_journal=central)
        sink = LocalAuditJournalPort(self.audit)
        self.users = UserService(st_users, security_journal=sink)
        self.firmware = FirmwareService(st_fw, security_journal=sink)
        self.certification = CertificationService(
            st_cert,
            security_journal=sink,
            firmware_row_fetch=self.firmware.get_row_dict,
        )
        self.registry = DroneRegistryService(
            st_reg,
            security_journal=sink,
            certificate_snapshot=self.certification.get_certificate_snapshot,
            firmware_row=self.firmware.get_row_dict,
        )
        self.purchase = PurchaseService(
            st_pur,
            security_journal=sink,
            registry=self.registry,
        )
        # для тестов/расширений — держим ссылку на «основной» storage как audit
        self.storage = st_audit

    @property
    def jwt_secret(self) -> str:
        """Секрет подписи JWT; в dev достаточно ненулевого значения по умолчанию."""
        return os.environ.get("JWT_SECRET", "uas_dev_company_dev_jwt_change_me_in_production").strip()
