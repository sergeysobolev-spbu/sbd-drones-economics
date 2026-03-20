from __future__ import annotations

"""Сущность `CustomerEntity`: приём заказа и форвардинг в `AggregatorEntity`."""

from typing import Any, Dict

from actions import RECEIVE_ORDER, PLACE_ORDER
from base_entity import BaseEntity


class CustomerEntity(BaseEntity):
    """
    Заказчик: принимает `receive_order`, форвардит его в Агрегатор и
    возвращает результат обратно вызывающему (оркестратору/главному процессу).
    """

    def handle_request(self, msg: Dict[str, Any]) -> None:
        action = msg.get("action")
        if action != PLACE_ORDER:
            self.send_response(
                request_msg=msg,
                payload={"status": "error", "error": "unknown_action"},
            )
            return

        order = msg["payload"]["order"]
        scenario_security_goals = msg["payload"]["scenario_security_goals"]
        max_price = msg["payload"].get("max_price")

        # Пересылаем Агрегатору
        res = self.rpc_send_wait(
            receiver="aggregator",
            action=RECEIVE_ORDER,
            payload={
                "order": order,
                "scenario_security_goals": scenario_security_goals,
                "max_price": max_price,
            },
            timeout_s=180.0,
        )

        self.send_response(request_msg=msg, payload=res)

