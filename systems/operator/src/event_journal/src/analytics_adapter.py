from __future__ import annotations

from typing import Any, Dict, Optional

import logging

try:
    import requests
except Exception:  # pragma: no cover - requests обязан быть в dev-окружении, но делаем защиту
    requests = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class AnalyticsAdapter:
    """
    Простая обёртка над HTTP‑API Analytics.

    На данном этапе реализована базовая отправка события;
    детали URL/аутентификации берутся из config.
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def send_event(self, event: Dict[str, Any]) -> bool:
        if requests is None:
            logger.warning("AnalyticsAdapter: requests is not available, skipping send_event")
            return False

        url = f"{self.base_url}/api/events"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = requests.post(url, json=event, headers=headers, timeout=self.timeout)
            if resp.status_code >= 200 and resp.status_code < 300:
                return True
            logger.warning("AnalyticsAdapter: non-success status %s: %s", resp.status_code, resp.text)
            return False
        except Exception as exc:
            logger.warning("AnalyticsAdapter: failed to send event: %s", exc)
            return False
