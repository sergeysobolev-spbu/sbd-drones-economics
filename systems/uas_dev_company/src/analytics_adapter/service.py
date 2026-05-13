"""Граница выхода к внешнему журналу DroneAnalytics."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from shared.bus_integration_adapters import BusDroneAnalyticsClient
from shared.integration_adapters import DroneAnalyticsPort
from shared.storage import SQLiteStorage


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


class AnalyticsAdapterService:
    """Доставка событий в центральный журнал DroneAnalytics; сбои не прерывают доменную операцию."""

    def __init__(
        self,
        storage: SQLiteStorage,
        enabled: bool,
        url: str = "",
        api_key: str = "",
        client: DroneAnalyticsPort | None = None,
    ):
        self.storage = storage
        self.enabled = enabled
        self.url = (url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.client = client

    def post_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """POST /log/event (массив из одного элемента) или делегирование клиенту."""
        if self.client is not None:
            return self.client.post_event(event)
        if not self.enabled:
            return {"ok": False, "error": "analytics disabled", "status_code": 0}
        if not self.url:
            return {"ok": False, "error": "DRONE_ANALYTICS_URL is empty", "status_code": 0}
        if not self.api_key:
            return {"ok": False, "error": "DRONE_ANALYTICS_API_KEY is empty", "status_code": 0}
        body = json.dumps([event], ensure_ascii=False).encode("utf-8")
        req = Request(
            f"{self.url}/log/event",
            data=body,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-API-Key": self.api_key,
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=8) as resp:
                _ = resp.read()
                return {"ok": 200 <= resp.status < 300, "status_code": getattr(resp, "status", 200)}
        except HTTPError as exc:
            return {"ok": False, "error": str(exc.reason or exc), "status_code": exc.code}
        except URLError as exc:
            return {"ok": False, "error": str(exc.reason or exc), "status_code": 0}

    def try_emit(self, event: dict[str, Any]) -> None:
        """Зафиксировать попытку доставки в analytics_delivery; исключения подавляются."""
        try:
            if not self.enabled and self.client is None:
                with self.storage.connect() as connection:
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO analytics_delivery(id, enabled, url, last_status, last_error)
                        VALUES (1, 0, ?, 'disabled', '')
                        """,
                        (self.url,),
                    )
                return
            result = self.post_event(event)
            ok = bool(result.get("ok"))
            err = str(result.get("error") or "")
            status = "delivered" if ok else "failed"
            with self.storage.connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO analytics_delivery(id, enabled, url, last_status, last_error)
                    VALUES (1, ?, ?, ?, ?)
                    """,
                    (1 if self.enabled else 0, self.url, status, err[:2000]),
                )
        except Exception as exc:  # noqa: BLE001 — журнал не должен валить домен
            try:
                with self.storage.connect() as connection:
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO analytics_delivery(id, enabled, url, last_status, last_error)
                        VALUES (1, ?, ?, 'failed', ?)
                        """,
                        (1 if self.enabled else 0, self.url, str(exc)[:2000]),
                    )
            except Exception:
                pass

    def send(self, event: dict[str, Any]) -> dict[str, Any]:
        """Совместимость с предыдущими тестами и простыми вызовами."""
        if not self.enabled and self.client is None:
            with self.storage.connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO analytics_delivery(id, enabled, url, last_status, last_error)
                    VALUES (1, 0, ?, 'disabled', '')
                    """,
                    (self.url,),
                )
            return {"delivered": False, "status": "disabled", "error": "", "event": event}
        result = self.post_event(event)
        ok = bool(result.get("ok"))
        err = str(result.get("error") or "")
        status = "delivered" if ok else "failed"
        with self.storage.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO analytics_delivery(id, enabled, url, last_status, last_error)
                VALUES (1, ?, ?, ?, ?)
                """,
                (1 if self.enabled else 0, self.url, status, err[:2000]),
            )
        return {"delivered": ok, "status": status, "error": err, "event": event}


def analytics_adapter_service_from_env(storage: SQLiteStorage, bus: Any) -> AnalyticsAdapterService:
    """Сборка сервиса для воркера analytics_adapter (HTTP или шина к systems.drone_analytics)."""
    enabled = _truthy_env("DRONE_ANALYTICS_ENABLED", "false")
    url = os.environ.get("DRONE_ANALYTICS_URL", "").strip()
    api_key = os.environ.get("DRONE_ANALYTICS_API_KEY", "").strip()
    mode = os.environ.get("UAS_DRONE_ANALYTICS_TRANSPORT", "http").strip().lower()
    if mode == "bus":
        client: DroneAnalyticsPort | None = BusDroneAnalyticsClient(bus=bus)
        return AnalyticsAdapterService(storage, enabled, url=url, api_key=api_key, client=client)
    return AnalyticsAdapterService(storage, enabled, url=url, api_key=api_key)
