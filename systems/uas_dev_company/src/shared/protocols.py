"""Протоколы IPC без привязки к пакетам доменов (Задача 23: НДБ-код не тянуть в ДДБ-образы через импорты)."""

from __future__ import annotations

from typing import Any, Protocol


class SupportsAnalyticsEmit(Protocol):
    def try_emit(self, event: dict[str, Any]) -> None: ...
