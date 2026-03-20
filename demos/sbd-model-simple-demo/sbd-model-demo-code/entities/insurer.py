from __future__ import annotations

"""Сущность `InsurerEntity` (Страховщик): выдаёт страховой quote (заглушка)."""

from typing import Any, Dict

from actions import REQUEST_INSURANCE_QUOTE
from base_entity import BaseEntity


class InsurerEntity(BaseEntity):
    """Страховщик: выдаёт quote (заглушка) по запросу."""

    def _register_handlers(self) -> None:
        self.register_handler(REQUEST_INSURANCE_QUOTE, self._on_insurance_quote)

    def _on_insurance_quote(self, msg: Dict[str, Any]) -> None:
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
