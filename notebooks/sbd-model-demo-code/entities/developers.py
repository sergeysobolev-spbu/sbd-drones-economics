from __future__ import annotations

"""Сущность `DevelopersEntity` (Разработчики БАС): заглушка покупки/подбора."""

from typing import Any, Dict

from actions import FIND_AVAILABLE_UAS, PURCHASE_UAS
from base_entity import BaseEntity


class DevelopersEntity(BaseEntity):
    """Разработчики БАС: заглушка методов покупки/подбора БАС."""

    def handle_request(self, msg: Dict[str, Any]) -> None:
        action = msg.get("action")

        if action == FIND_AVAILABLE_UAS:
            self.send_response(request_msg=msg, payload={"status": "ok", "suitable_uas": []})
            return

        if action == PURCHASE_UAS:
            model_id = msg["payload"].get("model_id")
            self.send_response(request_msg=msg, payload={"status": "ok", "purchased_uas": model_id})
            return

        self.send_response(request_msg=msg, payload={"status": "error", "error": "unknown_action"})

