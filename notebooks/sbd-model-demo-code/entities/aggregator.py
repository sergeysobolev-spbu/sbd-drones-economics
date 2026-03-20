from __future__ import annotations

"""Сущность `AggregatorEntity`: формирует цели безопасности заказа, собирает предложения и выбирает исполнителя."""

from typing import Any, Dict, List

from actions import RECEIVE_ORDER, PROPOSAL_REQUEST, ASSIGN_ORDER
from base_entity import BaseEntity


class AggregatorEntity(BaseEntity):
    """Агрегатор: формирует order_security_goals, собирает предложения и выбирает исполнителя."""

    def handle_request(self, msg: Dict[str, Any]) -> None:
        if msg.get("action") != RECEIVE_ORDER:
            self.send_response(request_msg=msg, payload={"status": "error", "error": "unknown_action"})
            return

        order = msg["payload"]["order"]
        scenario_security_goals: List[str] = msg["payload"]["scenario_security_goals"]
        max_price = msg["payload"].get("max_price")

        scenario_type = order.get("scenario_type", "agro")
        aggregator_constants = self.world["aggregator_constants"].get(scenario_type, [])
        order_security_goals = list(dict.fromkeys(list(scenario_security_goals) + list(aggregator_constants)))

        proposals: List[Dict[str, Any]] = []
        for ex_id in self.world["operator_ids"]:
            resp = self.rpc_send_wait(
                receiver=ex_id,
                action=PROPOSAL_REQUEST,
                payload={
                    "order": order,
                    "order_security_goals": order_security_goals,
                    "max_price": max_price,
                },
                timeout_s=20.0,
                expected_sender=ex_id,
            )
            if resp.get("status") == "ok":
                proposals.append(resp["proposal"])

        if not proposals:
            self.send_response(request_msg=msg, payload={"status": "error", "error": "no_proposals"})
            return

        def ok_offer(p: Dict[str, Any]) -> bool:
            if max_price is not None and float(p["price"]) > float(max_price):
                return False
            applied = set(p.get("applied_security_goals", []))
            return all(g in applied for g in order_security_goals)

        proposals = [p for p in proposals if ok_offer(p)]
        if not proposals:
            self.send_response(request_msg=msg, payload={"status": "error", "error": "no_acceptable_proposals"})
            return

        proposals.sort(key=lambda x: float(x["price"]))
        chosen = proposals[0]
        operator_id = chosen["operator_id"]

        completed = self.rpc_send_wait(
            receiver=operator_id,
            action=ASSIGN_ORDER,
            payload={
                "order": order,
                "order_security_goals": order_security_goals,
                "selected_uas": chosen["selected_uas"],
                "insurance_quote": chosen.get("insurance_quote", {}),
            },
            timeout_s=120.0,
            expected_sender=operator_id,
        )

        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "order_execution_completed": completed.get("order_execution_completed"),
                "selected_operator": operator_id,
                "order_security_goals": order_security_goals,
                "chosen_proposal": {
                    "proposal_id": chosen["proposal_id"],
                    "price": chosen["price"],
                    "margin_percent": chosen["margin_percent"],
                    "applied_security_goals": chosen["applied_security_goals"],
                },
            },
        )

