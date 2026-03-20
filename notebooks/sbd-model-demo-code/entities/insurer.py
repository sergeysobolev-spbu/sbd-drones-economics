from __future__ import annotations

"""Сущность `InsurerEntity` (Страховщик): выдаёт страховой quote (заглушка)."""

from typing import Any, Dict

from actions import REQUEST_INSURANCE_QUOTE
from base_entity import BaseEntity


class InsurerEntity(BaseEntity):
    """Страховщик: выдаёт quote (заглушка) по запросу."""

    def handle_request(self, msg: Dict[str, Any]) -> None:
        action = msg.get("action")
        if action != REQUEST_INSURANCE_QUOTE:
            self.send_response(request_msg=msg, payload={"status": "error", "error": "unknown_action"})
            return

        coverage = msg["payload"].get("coverage", {})
        base_premium = float(msg["payload"].get("base_premium", 1000.0))
        quote_id = f"quote-{msg['correlation_id'][:8]}"

        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "quote_id": quote_id,
                "premium": base_premium,
                "coverage": coverage,
                "valid_until": "2099-12-31T00:00:00Z",
            },
        )

