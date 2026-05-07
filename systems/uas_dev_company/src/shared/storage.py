"""SQLite storage for the UAS development company system."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


DEFAULT_DB_PATH = "resources/uas_dev_company.sqlite3"


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (firmware_id) REFERENCES firmware_versions(firmware_id)
);

CREATE TABLE IF NOT EXISTS certificates (
    certificate_id TEXT PRIMARY KEY,
    firmware_id TEXT NOT NULL,
    security_goals TEXT NOT NULL,
    signed_by TEXT NOT NULL,
    certificate_status TEXT NOT NULL DEFAULT 'active',
    effective_security_goals TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (firmware_id) REFERENCES firmware_versions(firmware_id)
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
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (firmware_id) REFERENCES firmware_versions(firmware_id),
    FOREIGN KEY (certificate_id) REFERENCES certificates(certificate_id)
);

CREATE TABLE IF NOT EXISTS vulnerability_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firmware_id TEXT NOT NULL,
    incident_type TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    correlation_id TEXT NOT NULL DEFAULT '',
    notification_status TEXT NOT NULL DEFAULT 'pending',
    regulator_decision TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (firmware_id) REFERENCES firmware_versions(firmware_id)
);

CREATE TABLE IF NOT EXISTS purchases (
    order_id TEXT PRIMARY KEY,
    serial_number TEXT NOT NULL,
    operator_username TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (serial_number) REFERENCES drones(serial_number),
    FOREIGN KEY (operator_username) REFERENCES users(username)
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

INSERT OR IGNORE INTO schema_version(version) VALUES (1);
"""


def default_db_path() -> Path:
    """Return SQLite path from environment."""
    return Path(os.environ.get("SQLITE_DB_PATH", DEFAULT_DB_PATH))


class SQLiteStorage:
    """Small SQLite wrapper with schema initialization."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()
        self._migrate_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection with row dictionaries enabled."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create all tables if they are missing."""
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def _migrate_schema(self) -> None:
        """Пошаговые миграции SQLite (v2: прошивка/ЦБ дрона; v3: регистрация, доставка, уязвимости)."""
        with self.connect() as connection:
            rows = connection.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
            current = int(rows["v"] if rows and rows["v"] is not None else 1)
            if current < 2:
                f_cols = {r[1] for r in connection.execute("PRAGMA table_info(firmware_versions)").fetchall()}
                if "source_repo_url" not in f_cols:
                    connection.execute(
                        "ALTER TABLE firmware_versions ADD COLUMN source_repo_url TEXT NOT NULL DEFAULT ''"
                    )
                if "source_commit" not in f_cols:
                    connection.execute(
                        "ALTER TABLE firmware_versions ADD COLUMN source_commit TEXT NOT NULL DEFAULT ''"
                    )
                d_cols = {r[1] for r in connection.execute("PRAGMA table_info(drones)").fetchall()}
                if "security_goals" not in d_cols:
                    connection.execute(
                        "ALTER TABLE drones ADD COLUMN security_goals TEXT NOT NULL DEFAULT '[]'"
                    )
                    connection.execute(
                        """
                        UPDATE drones SET security_goals = (
                            SELECT security_goals FROM firmware_versions f
                            WHERE f.firmware_id = drones.firmware_id
                        )
                        WHERE security_goals = '[]' OR security_goals = ''
                        """
                    )
                connection.execute("INSERT INTO schema_version(version) VALUES (2)")
                current = 2

            if current < 3:
                c_cols = {r[1] for r in connection.execute("PRAGMA table_info(certificates)").fetchall()}
                if "certificate_status" not in c_cols:
                    connection.execute(
                        "ALTER TABLE certificates ADD COLUMN certificate_status TEXT NOT NULL DEFAULT 'active'"
                    )
                if "effective_security_goals" not in c_cols:
                    connection.execute(
                        "ALTER TABLE certificates ADD COLUMN effective_security_goals TEXT NOT NULL DEFAULT '[]'"
                    )
                connection.execute(
                    """
                    UPDATE certificates
                    SET effective_security_goals = security_goals
                    WHERE effective_security_goals = '[]' OR effective_security_goals = ''
                    """
                )
                d_cols = {r[1] for r in connection.execute("PRAGMA table_info(drones)").fetchall()}
                extra_drone = [
                    ("registration_id", "TEXT NOT NULL DEFAULT ''"),
                    ("registration_status", "TEXT NOT NULL DEFAULT 'pending_regulator'"),
                    ("registration_version", "INTEGER NOT NULL DEFAULT 0"),
                    ("regulator_reason", "TEXT NOT NULL DEFAULT ''"),
                    ("owner_operator_id", "TEXT NOT NULL DEFAULT ''"),
                    ("last_regulator_correlation_id", "TEXT NOT NULL DEFAULT ''"),
                    ("hardware_config", "TEXT NOT NULL DEFAULT '{}'"),
                    ("destination_droneport_id", "TEXT NOT NULL DEFAULT ''"),
                    ("delivery_status", "TEXT NOT NULL DEFAULT 'none'"),
                    ("delivered_at", "TEXT NOT NULL DEFAULT ''"),
                    ("physical_safety_responsibility", "TEXT NOT NULL DEFAULT 'developer'"),
                ]
                for name, decl in extra_drone:
                    if name not in d_cols:
                        connection.execute(f"ALTER TABLE drones ADD COLUMN {name} {decl}")
                connection.execute(
                    """
                    UPDATE drones
                    SET
                        registration_status = 'registered_by_regulator',
                        registration_id = 'legacy-' || serial_number,
                        registration_version = 1
                    WHERE registration_id = '' OR registration_id IS NULL
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vulnerability_incidents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        firmware_id TEXT NOT NULL,
                        incident_type TEXT NOT NULL,
                        description TEXT NOT NULL DEFAULT '',
                        correlation_id TEXT NOT NULL DEFAULT '',
                        notification_status TEXT NOT NULL DEFAULT 'pending',
                        regulator_decision TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (firmware_id) REFERENCES firmware_versions(firmware_id)
                    )
                    """
                )
                connection.execute("INSERT INTO schema_version(version) VALUES (3)")


def encode_json(value: Any) -> str:
    """Encode JSON using a stable unicode-preserving representation."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def decode_json(value: str) -> Any:
    """Decode JSON stored in SQLite."""
    return json.loads(value)
