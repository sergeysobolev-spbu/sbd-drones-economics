"""Обработчики сообщений firmware_ingestion."""

from __future__ import annotations

from typing import Any, Callable

from firmware_ingestion.firmware_service import FirmwareService
from shared.storage import SQLiteStorage
from shared.topics import Actions
from shared.worker_deps import WorkerServiceDeps


def build_firmware_ingestion_handlers(
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    firmware = FirmwareService(storage, security_journal=deps.security_journal)

    def submit_firmware(payload: dict[str, Any]) -> dict[str, Any]:
        inner = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        return firmware.submit(
            str(payload["actor_role"]),
            str(payload["submitted_by"]),
            inner,
        )

    def get_firmware_row(payload: dict[str, Any]) -> dict[str, Any]:
        fid = str(payload.get("firmware_id") or "").strip()
        row = firmware.get_row_dict(fid)
        return {"row": row}

    return {
        Actions.SUBMIT_FIRMWARE: submit_firmware,
        Actions.GET_FIRMWARE_ROW: get_firmware_row,
    }
