"""Обработчики сообщений домена user_management."""

from __future__ import annotations

from typing import Any, Callable

from user_management.user_service import UserService
from shared.storage import SQLiteStorage
from shared.topics import Actions
from shared.worker_deps import WorkerServiceDeps


def build_user_management_handlers(
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    users = UserService(storage, security_journal=deps.security_journal)

    def bootstrap_admin(payload: dict[str, Any]) -> dict[str, Any]:
        return users.bootstrap_admin(str(payload["username"]), str(payload["password"]))

    def authenticate(payload: dict[str, Any]) -> dict[str, Any]:
        return users.authenticate(str(payload["username"]), str(payload["password"]))

    def create_user(payload: dict[str, Any]) -> dict[str, Any]:
        return users.create_user(
            str(payload["actor_role"]),
            str(payload["username"]).strip(),
            str(payload["role"]).strip(),
            str(payload["password"]),
        )

    def list_users(payload: dict[str, Any]) -> dict[str, Any]:
        role = str(payload["actor_role"])
        return {"users": users.list_users(role)}

    def enable_user(payload: dict[str, Any]) -> dict[str, Any]:
        return users.set_user_active(
            str(payload["actor_role"]),
            str(payload["username"]),
            True,
        )

    def disable_user(payload: dict[str, Any]) -> dict[str, Any]:
        return users.set_user_active(
            str(payload["actor_role"]),
            str(payload["username"]),
            False,
        )

    def delete_user(payload: dict[str, Any]) -> dict[str, Any]:
        return users.delete_user(str(payload["actor_role"]), str(payload["username"]))

    return {
        Actions.BOOTSTRAP_ADMIN: bootstrap_admin,
        Actions.AUTHENTICATE: authenticate,
        Actions.CREATE_USER: create_user,
        Actions.LIST_USERS: list_users,
        Actions.ENABLE_USER: enable_user,
        Actions.DISABLE_USER: disable_user,
        Actions.DELETE_USER: delete_user,
    }
