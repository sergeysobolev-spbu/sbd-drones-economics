from __future__ import annotations

"""Сущность `CustomerEntity`: приём заказа и форвардинг в `AggregatorEntity`."""

from typing import Any, Dict

from actions import RECEIVE_ORDER, PLACE_ORDER
from base_entity import BaseEntity


class CustomerEntity(BaseEntity):
    """
    Заказчик: принимает `place_order`, форвардит в Агрегатор и
    возвращает результат оркестратору.
    """

    def _register_handlers(self) -> None:
        self.register_handler(PLACE_ORDER, self._on_place_order)

    def _on_place_order(self, msg: Dict[str, Any]) -> None:
        order = msg["payload"]["order"]
        scenario_security_goals = msg["payload"]["scenario_security_goals"]
        max_price = msg["payload"].get("max_price")
        trace_id = msg.get("trace_id")
        parent_span_id = msg.get("span_id")

        res = self.rpc_send_wait(
            receiver="aggregator",
            action=RECEIVE_ORDER,
            payload={
                "order": order,
                "scenario_security_goals": scenario_security_goals,
                "max_price": max_price,
            },
            timeout_s=180.0,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )

        self.send_response(request_msg=msg, payload=res)
