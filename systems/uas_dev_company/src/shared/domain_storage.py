"""Per-domain SQLite roots (Задача 22): отдельный каталог и файл БД на домен безопасности."""

from __future__ import annotations

import os
from pathlib import Path

# Идентификаторы подкаталогов под UAS_DOMAIN_DATA_ROOT (виртуальная ФС на домен).
USER_MANAGEMENT = "user_management"
FIRMWARE_INGESTION = "firmware_ingestion"
CERTIFICATION_SERVICE = "certification_service"
DRONE_REGISTRY = "drone_registry"
PURCHASE_SERVICE = "purchase_service"
AUDIT_LOG = "audit_log"
ANALYTICS_ADAPTER = "analytics_adapter"

TOPIC_TO_DOMAIN: dict[str, str] = {}


def _register_topics() -> None:
    from shared.topics import ComponentTopics

    TOPIC_TO_DOMAIN[ComponentTopics.USER_MANAGEMENT] = USER_MANAGEMENT
    TOPIC_TO_DOMAIN[ComponentTopics.FIRMWARE_INGESTION] = FIRMWARE_INGESTION
    TOPIC_TO_DOMAIN[ComponentTopics.CERTIFICATION_SERVICE] = CERTIFICATION_SERVICE
    TOPIC_TO_DOMAIN[ComponentTopics.DRONE_REGISTRY] = DRONE_REGISTRY
    TOPIC_TO_DOMAIN[ComponentTopics.PURCHASE_SERVICE] = PURCHASE_SERVICE
    TOPIC_TO_DOMAIN[ComponentTopics.AUDIT_LOG] = AUDIT_LOG
    TOPIC_TO_DOMAIN[ComponentTopics.ANALYTICS_ADAPTER] = ANALYTICS_ADAPTER


_register_topics()


def domain_id_for_worker_topic(topic: str) -> str:
    if topic in TOPIC_TO_DOMAIN:
        return TOPIC_TO_DOMAIN[topic]
    dom = os.environ.get("UAS_STORAGE_DOMAIN", "").strip()
    if dom:
        return dom
    raise ValueError(f"Unknown worker topic for storage domain mapping: {topic!r}")


def domain_data_root() -> Path:
    return Path(os.environ.get("UAS_DOMAIN_DATA_ROOT", "resources/domains"))


def domain_db_path(domain_id: str) -> Path:
    return domain_data_root() / domain_id / "data.sqlite3"


def gateway_sqlite_paths_parent(root: Path | None = None) -> Path:
    """База для режима ApiContext: отдельные файлы под каждый домен."""
    base = root if root is not None else domain_data_root()
    return base
