"""Контракт минимальной доставки событий во внешний журнал (процессный или IPC)."""

from __future__ import annotations

from typing import Any, Protocol


class SupportsAnalyticsEmit(Protocol):
    def try_emit(self, event: dict[str, Any]) -> None: ...
