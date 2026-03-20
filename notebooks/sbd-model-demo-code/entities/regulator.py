from __future__ import annotations

"""Сущность `RegulatorEntity`: возвращает system_security_goals (цели безопасности)."""

from typing import Any, Dict

from actions import GET_SECURITY_GOALS
from base_entity import BaseEntity


class RegulatorEntity(BaseEntity):
    """Регулятор: возвращает наборы целей безопасности для систем."""

    def handle_request(self, msg: Dict[str, Any]) -> None:
        if msg.get("action") != GET_SECURITY_GOALS:
            self.send_response(request_msg=msg, payload={"status": "error", "error": "unknown_action"})
            return

        system_key = msg["payload"].get("system_key")
        goals = self.world["system_security_goals"].get(system_key, [])

        self.send_response(
            request_msg=msg,
            payload={"status": "ok", "security_goals": [{"goal_id": g} for g in goals]},
        )

