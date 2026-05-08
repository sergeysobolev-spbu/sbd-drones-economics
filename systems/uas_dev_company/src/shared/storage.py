"""SQLite storage: отдельная схема на домен безопасности (Задача 22)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from shared import domain_storage as _domains

_SCHEMA_HEADER = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO schema_version(version) VALUES (1);
"""

SCHEMA_USER_MANAGEMENT = _SCHEMA_HEADER + """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SCHEMA_FIRMWARE = _SCHEMA_HEADER + """
CREATE TABLE IF NOT EXISTS firmware_versions (
    firmware_id TEXT PRIMARY KEY,
    supplier TEXT NOT NULL,
    drone_type TEXT NOT NULL,
    version TEXT NOT NULL,
    firmware_hash TEXT NOT NULL DEFAULT '',
    source_repo_url TEXT NOT NULL DEFAULT '',
    source_commit TEXT NOT NULL DEFAULT '',
    security_goals TEXT NOT NULL,
    authenticity_proof TEXT NOT NULL,
    submitted_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SCHEMA_CERTIFICATION = _SCHEMA_HEADER + """
CREATE TABLE IF NOT EXISTS certification_requests (
    request_id TEXT PRIMARY KEY,
    firmware_id TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,
    certification_cost REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS certificates (
    certificate_id TEXT PRIMARY KEY,
    firmware_id TEXT NOT NULL,
    security_goals TEXT NOT NULL,
    signed_by TEXT NOT NULL,
    certificate_status TEXT NOT NULL DEFAULT 'active',
    effective_security_goals TEXT NOT NULL DEFAULT '[]',
    supplier TEXT NOT NULL DEFAULT '',
    drone_type TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    firmware_hash TEXT NOT NULL DEFAULT '',
    source_repo_url TEXT NOT NULL DEFAULT '',
    source_commit TEXT NOT NULL DEFAULT '',
    submitted_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS vulnerability_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firmware_id TEXT NOT NULL,
    incident_type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    notification_status TEXT NOT NULL DEFAULT 'pending',
    regulator_decision TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SCHEMA_DRONE_REGISTRY = _SCHEMA_HEADER + """
CREATE TABLE IF NOT EXISTS drones (
    serial_number TEXT PRIMARY KEY,
    drone_type TEXT NOT NULL,
    firmware_id TEXT NOT NULL,
    certificate_id TEXT NOT NULL,
    security_goals TEXT NOT NULL,
    price REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    registration_id TEXT NOT NULL DEFAULT '',
    registration_status TEXT NOT NULL DEFAULT 'pending_regulator',
    registration_version INTEGER NOT NULL DEFAULT 0,
    regulator_reason TEXT NOT NULL DEFAULT '',
    owner_operator_id TEXT NOT NULL DEFAULT '',
    last_regulator_correlation_id TEXT NOT NULL DEFAULT '',
    hardware_config TEXT NOT NULL DEFAULT '{}',
    destination_droneport_id TEXT NOT NULL DEFAULT '',
    delivery_status TEXT NOT NULL DEFAULT 'none',
    delivered_at TEXT NOT NULL DEFAULT '',
    physical_safety_responsibility TEXT NOT NULL DEFAULT 'developer',
    certificate_status TEXT NOT NULL DEFAULT 'active',
    certificate_effective_security_goals TEXT NOT NULL DEFAULT '[]',
    certificate_security_goals TEXT NOT NULL DEFAULT '[]',
    firmware_supplier TEXT NOT NULL DEFAULT '',
    firmware_hash TEXT NOT NULL DEFAULT '',
    firmware_security_goals TEXT NOT NULL DEFAULT '[]',
    certification_cost REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SCHEMA_PURCHASE = _SCHEMA_HEADER + """
CREATE TABLE IF NOT EXISTS purchases (
    order_id TEXT PRIMARY KEY,
    serial_number TEXT NOT NULL,
    operator_username TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SCHEMA_AUDIT = _SCHEMA_HEADER + """
CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    source TEXT NOT NULL,
    subject TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SCHEMA_ANALYTICS = _SCHEMA_HEADER + """
CREATE TABLE IF NOT EXISTS analytics_delivery (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    last_status TEXT NOT NULL DEFAULT 'disabled',
    last_error TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

MONOLITH = "monolith"

MONOLITH_BODY = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS firmware_versions (
    firmware_id TEXT PRIMARY KEY,
    supplier TEXT NOT NULL,
    drone_type TEXT NOT NULL,
    version TEXT NOT NULL,
    firmware_hash TEXT NOT NULL DEFAULT '',
    source_repo_url TEXT NOT NULL DEFAULT '',
    source_commit TEXT NOT NULL DEFAULT '',
    security_goals TEXT NOT NULL,
    authenticity_proof TEXT NOT NULL,
    submitted_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS certification_requests (
    request_id TEXT PRIMARY KEY,
    firmware_id TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,
    certification_cost REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS certificates (
    certificate_id TEXT PRIMARY KEY,
    firmware_id TEXT NOT NULL,
    security_goals TEXT NOT NULL,
    signed_by TEXT NOT NULL,
    certificate_status TEXT NOT NULL DEFAULT 'active',
    effective_security_goals TEXT NOT NULL DEFAULT '[]',
    supplier TEXT NOT NULL DEFAULT '',
    drone_type TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    firmware_hash TEXT NOT NULL DEFAULT '',
    source_repo_url TEXT NOT NULL DEFAULT '',
    source_commit TEXT NOT NULL DEFAULT '',
    submitted_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS vulnerability_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firmware_id TEXT NOT NULL,
    incident_type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    notification_status TEXT NOT NULL DEFAULT 'pending',
    regulator_decision TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS drones (
    serial_number TEXT PRIMARY KEY,
    drone_type TEXT NOT NULL,
    firmware_id TEXT NOT NULL,
    certificate_id TEXT NOT NULL,
    security_goals TEXT NOT NULL,
    price REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    registration_id TEXT NOT NULL DEFAULT '',
    registration_status TEXT NOT NULL DEFAULT 'pending_regulator',
    registration_version INTEGER NOT NULL DEFAULT 0,
    regulator_reason TEXT NOT NULL DEFAULT '',
    owner_operator_id TEXT NOT NULL DEFAULT '',
    last_regulator_correlation_id TEXT NOT NULL DEFAULT '',
    hardware_config TEXT NOT NULL DEFAULT '{}',
    destination_droneport_id TEXT NOT NULL DEFAULT '',
    delivery_status TEXT NOT NULL DEFAULT 'none',
    delivered_at TEXT NOT NULL DEFAULT '',
    physical_safety_responsibility TEXT NOT NULL DEFAULT 'developer',
    certificate_status TEXT NOT NULL DEFAULT 'active',
    certificate_effective_security_goals TEXT NOT NULL DEFAULT '[]',
    certificate_security_goals TEXT NOT NULL DEFAULT '[]',
    firmware_supplier TEXT NOT NULL DEFAULT '',
    firmware_hash TEXT NOT NULL DEFAULT '',
    firmware_security_goals TEXT NOT NULL DEFAULT '[]',
    certification_cost REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS purchases (
    order_id TEXT PRIMARY KEY,
    serial_number TEXT NOT NULL,
    operator_username TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    source TEXT NOT NULL,
    subject TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS analytics_delivery (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    last_status TEXT NOT NULL DEFAULT 'disabled',
    last_error TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SCHEMA_MONOLITH = _SCHEMA_HEADER + MONOLITH_BODY

DOMAIN_SCHEMA: dict[str, str] = {
    _domains.USER_MANAGEMENT: SCHEMA_USER_MANAGEMENT,
    _domains.FIRMWARE_INGESTION: SCHEMA_FIRMWARE,
    _domains.CERTIFICATION_SERVICE: SCHEMA_CERTIFICATION,
    _domains.DRONE_REGISTRY: SCHEMA_DRONE_REGISTRY,
    _domains.PURCHASE_SERVICE: SCHEMA_PURCHASE,
    _domains.AUDIT_LOG: SCHEMA_AUDIT,
    _domains.ANALYTICS_ADAPTER: SCHEMA_ANALYTICS,
    MONOLITH: SCHEMA_MONOLITH,
}


def resolve_storage_path(domain_id: str | None, db_path: str | Path | None) -> Path:
    if db_path is not None:
        return Path(db_path)
    if not domain_id:
        raise ValueError("Нужен domain_id или db_path")
    return _domains.domain_db_path(domain_id)


class SQLiteStorage:
    """SQLite: одна схема на домен (или monolith для одного файла со всеми таблицами)."""

    def __init__(self, domain_id: str, db_path: str | Path | None = None):
        self.domain_id = domain_id
        self.db_path = resolve_storage_path(domain_id, db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._schema = DOMAIN_SCHEMA[domain_id]
        except KeyError as e:
            raise ValueError(f"Неизвестный domain_id схемы: {domain_id!r}") from e
        self.initialize()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(self._schema)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        finally:
            connection.close()


def encode_json(value: Any) -> str:
    """Encode JSON using a stable unicode-preserving representation."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def decode_json(value: str) -> Any:
    """Decode JSON stored in SQLite."""
    return json.loads(value)
