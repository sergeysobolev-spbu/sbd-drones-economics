"""Домен пользователей и ролей (ЦБ-2)."""

from __future__ import annotations

from typing import Any

from shared.audit_log_ipc import SupportsSecurityJournal
from shared.models import SecurityEvent
from shared.storage import SQLiteStorage
from shared.tcb import AuthorizationError, hash_password, require_role, verify_password
from shared.topics import Roles


class UserService:
    """Manage users and role-based authentication."""

    def __init__(self, storage: SQLiteStorage, security_journal: SupportsSecurityJournal | None = None):
        self.storage = storage
        self.security_journal = security_journal

    def bootstrap_admin(self, username: str, password: str) -> dict[str, Any]:
        """Create the first administrator if no users exist."""
        with self.storage.connect() as connection:
            count = connection.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if count:
            raise AuthorizationError("admin bootstrap is allowed only for an empty database")
        result = self._create_user(username, Roles.ADMIN, password)
        if self.security_journal:
            self.security_journal.try_record(
                SecurityEvent("admin_bootstrapped", "info", "user_management", username, "")
            )
        return result

    def create_user(self, actor_role: str, username: str, role: str, password: str) -> dict[str, Any]:
        """Create a user; only administrators are allowed."""
        require_role(actor_role, Roles.ADMIN)
        result = self._create_user(username, role, password)
        if self.security_journal:
            self.security_journal.try_record(
                SecurityEvent("user_created", "info", "user_management", username, f"role={role}")
            )
        return result

    def _create_user(self, username: str, role: str, password: str) -> dict[str, Any]:
        if role not in Roles.ALL:
            raise ValueError(f"unsupported role: {role}")
        password_hash = hash_password(password)
        with self.storage.connect() as connection:
            connection.execute(
                """
                INSERT INTO users(username, role, password_hash, is_active)
                VALUES (?, ?, ?, 1)
                """,
                (username, role, password_hash),
            )
        return {"username": username, "role": role, "is_active": True}

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate a user and return role information."""
        with self.storage.connect() as connection:
            row = connection.execute(
                "SELECT username, role, password_hash, is_active FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None or not row["is_active"] or not verify_password(password, row["password_hash"]):
            raise AuthorizationError("invalid credentials")
        return {"username": row["username"], "role": row["role"]}

    def list_users(self, actor_role: str) -> list[dict[str, Any]]:
        """List users without exposing password hashes."""
        require_role(actor_role, Roles.ADMIN)
        with self.storage.connect() as connection:
            rows = connection.execute(
                "SELECT username, role, is_active FROM users ORDER BY username"
            ).fetchall()
        return [dict(row) for row in rows]

    def set_user_active(self, actor_role: str, username: str, is_active: bool) -> dict[str, Any]:
        """Activate or block a user account; only administrators."""
        require_role(actor_role, Roles.ADMIN)
        with self.storage.connect() as connection:
            row = connection.execute(
                "SELECT username, role, is_active FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                raise ValueError("user is not found")
            if not is_active and row["role"] == Roles.ADMIN:
                active_admins = connection.execute(
                    """
                    SELECT COUNT(*) AS c FROM users
                    WHERE role = ? AND is_active = 1
                    """,
                    (Roles.ADMIN,),
                ).fetchone()["c"]
                if active_admins <= 1:
                    raise ValueError("cannot deactivate the last administrator")
            connection.execute(
                """
                UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
                """,
                (1 if is_active else 0, username),
            )
        if self.security_journal:
            self.security_journal.try_record(
                SecurityEvent(
                    "user_active_changed",
                    "warning" if not is_active else "info",
                    "user_management",
                    username,
                    f"is_active={is_active}",
                )
            )
        return {"username": username, "is_active": is_active}

    def delete_user(self, actor_role: str, username: str) -> dict[str, Any]:
        """Remove a user permanently; only administrators."""
        require_role(actor_role, Roles.ADMIN)
        with self.storage.connect() as connection:
            row = connection.execute(
                "SELECT username, role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                raise ValueError("user is not found")
            if row["role"] == Roles.ADMIN:
                total_admins = connection.execute(
                    "SELECT COUNT(*) AS c FROM users WHERE role = ?",
                    (Roles.ADMIN,),
                ).fetchone()["c"]
                if total_admins <= 1:
                    raise ValueError("cannot delete the last administrator")
            purchases = connection.execute(
                "SELECT COUNT(*) AS c FROM purchases WHERE operator_username = ?",
                (username,),
            ).fetchone()["c"]
            if purchases:
                raise ValueError("cannot delete user with purchase history")
            connection.execute("DELETE FROM users WHERE username = ?", (username,))
        if self.security_journal:
            self.security_journal.try_record(
                SecurityEvent("user_deleted", "alert", "user_management", username, "")
            )
        return {"username": username, "deleted": True}
