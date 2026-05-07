"""Обработчики сообщений drone_registry."""

from __future__ import annotations

from typing import Any, Callable

from shared.services import DroneRegistryService
from shared.storage import SQLiteStorage
from shared.topics import Actions
from shared.worker_deps import WorkerServiceDeps


def build_drone_registry_handlers(
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    reg = DroneRegistryService(
        storage,
        regulator=deps.regulator,
        security_journal=deps.security_journal,
        operator_fleet=deps.operator_fleet,
    )

    def register_drone(payload: dict[str, Any]) -> dict[str, Any]:
        inner = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        return reg.register(str(payload["actor_role"]), inner)

    def list_drones(payload: dict[str, Any]) -> dict[str, Any]:
        rows = reg.list_registered(str(payload["actor_role"]))
        return {"drones": rows}

    return {
        Actions.REGISTER_DRONE: register_drone,
        Actions.LIST_REGISTERED_DRONES: list_drones,
    }
