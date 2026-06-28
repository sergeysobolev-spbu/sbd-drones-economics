from __future__ import annotations

"""Сущность `OperatorEntity` (Оператор): предложение по заказу и исполнение."""

from typing import Any, Dict, List, Set, Tuple

from actions import (
    PROPOSAL_REQUEST,
    ASSIGN_ORDER,
    REQUEST_INSURANCE_QUOTE,
    GET_AVAILABLE_UAS,
    MISSION_PLANNING,
    VALIDATE_MISSION,
    PREPARE_DISPATCH,
    AGRO_MISSION_RECEIVED,
    REQUEST_UAS_PURCHASE,
    ASSIGN_UAS_TO_DRONEPORT,
)
from base_entity import BaseEntity


class OperatorEntity(BaseEntity):
    """Оператор: предложение (proposal) и исполнение назначенного заказа."""

    def __init__(
        self,
        *,
        entity_id: str,
        inbox_queue: Any,
        broker_in_queue: Any,
        reply_queue: Any,
        reply_queue_name: str,
        world: Dict[str, Any],
    ) -> None:
        super().__init__(
            entity_id=entity_id,
            inbox_queue=inbox_queue,
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queue,
            reply_queue_name=reply_queue_name,
            world=world,
        )
        self.operator_security_goals: Set[str] = set(
            self.world["operators"][self.entity_id]["system_security_goals"]
        )

    def _register_handlers(self) -> None:
        self.register_handler(PROPOSAL_REQUEST, self._on_proposal_request)
        self.register_handler(ASSIGN_ORDER, self._on_assign_order)
        self.register_handler(REQUEST_UAS_PURCHASE, self._on_uas_purchase)

    def _select_best_uas(
        self,
        *,
        order: Dict[str, Any],
        order_security_goals: List[str],
        trace_id: str | None,
        parent_span_id: str | None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        del order_security_goals  # reserved for future filtering
        task_type = order.get("scenario_type", "agro")
        destination = order.get("destination")

        candidates: List[Tuple[str, Dict[str, Any]]] = []
        for dp_id in self.world["dronports"].keys():
            resp = self.rpc_send_wait(
                receiver=dp_id,
                action=GET_AVAILABLE_UAS,
                payload={"location": destination, "task_type": task_type},
                timeout_s=10.0,
                expected_sender=dp_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
            )
            if resp.get("status") != "ok":
                continue
            for u in resp.get("available_uas", []):
                candidates.append((dp_id, u))

        if not candidates:
            raise ValueError("no_suitable_uas")

        dp_id, uas = min(
            candidates,
            key=lambda item: float(item[1].get("base_cost", 0.0)),
        )
        return dp_id, uas["uas_id"], uas

    def _on_proposal_request(self, msg: Dict[str, Any]) -> None:
        order = msg["payload"]["order"]
        order_security_goals = msg["payload"]["order_security_goals"]
        max_price = msg["payload"].get("max_price")
        trace_id = msg.get("trace_id")
        parent_span_id = msg.get("span_id")

        if any(g not in self.operator_security_goals for g in order_security_goals):
            self.send_response(
                request_msg=msg,
                payload={
                    "status": "error",
                    "error": "security_goal_coverage_mismatch",
                    "rejection": {"rejected_by_security_goals": list(order_security_goals)},
                },
            )
            return

        try:
            selected_droneport_id, uas_id, uas = self._select_best_uas(
                order=order,
                order_security_goals=order_security_goals,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
            )
        except Exception as e:  # noqa: BLE001
            self.send_response(
                request_msg=msg,
                payload={"status": "error", "error": "no_suitable_uas", "details": str(e)},
            )
            return

        quote = self.rpc_send_wait(
            receiver="insurer",
            action=REQUEST_INSURANCE_QUOTE,
            payload={
                "mission_candidate": {
                    "order_id": order["id"],
                    "scenario_type": order.get("scenario_type"),
                },
                "uas_id": uas_id,
                "order_security_goals": order_security_goals,
                "coverage": order.get("coverage", {}),
                "base_premium": 1000.0,
            },
            timeout_s=15.0,
            expected_sender="insurer",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
        premium = float(quote.get("premium", 0.0))

        base_cost = float(uas.get("base_cost", 10000.0))
        total_cost = base_cost + premium
        margin = 0.10
        price = total_cost * (1.0 + margin)

        if max_price is not None and price > float(max_price):
            self.send_response(
                request_msg=msg,
                payload={"status": "error", "error": "max_price_exceeded", "price": price},
            )
            return

        proposal = {
            "proposal_id": f"prop-{self.entity_id}-{msg['correlation_id'][:6]}",
            "operator_id": self.entity_id,
            "selected_uas": {"uas_id": uas_id, "droneport_id": selected_droneport_id},
            "total_cost": total_cost,
            "price": price,
            "margin_percent": margin * 100.0,
            "applied_security_goals": list(order_security_goals),
            "insurance_quote": {"quote_id": quote.get("quote_id"), "premium": premium},
        }

        self.send_response(request_msg=msg, payload={"status": "ok", "proposal": proposal})

    def _on_assign_order(self, msg: Dict[str, Any]) -> None:
        order = msg["payload"]["order"]
        order_security_goals = msg["payload"]["order_security_goals"]
        selected_uas = msg["payload"]["selected_uas"]
        insurance_quote = msg["payload"].get("insurance_quote", {})
        trace_id = msg.get("trace_id")
        parent_span_id = msg.get("span_id")

        mission = self.rpc_send_wait(
            receiver="gcs",
            action=MISSION_PLANNING,
            payload={
                "order": order,
                "selected_uas": selected_uas,
                "order_security_goals": order_security_goals,
            },
            timeout_s=30.0,
            expected_sender="gcs",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
        mission_details = mission["mission_details"]

        approved = self.rpc_send_wait(
            receiver="atm",
            action=VALIDATE_MISSION,
            payload={
                "mission_details": mission_details,
                "mission_security_goals": mission.get("mission_security_goals", []),
            },
            timeout_s=30.0,
            expected_sender="atm",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
        if not approved.get("approved"):
            self.send_response(request_msg=msg, payload={"status": "error", "error": "mission_rejected"})
            return

        if insurance_quote.get("quote_id"):
            insurance_payment_id = f"pay-{insurance_quote.get('quote_id','')[-6:]}"
        else:
            insurance_payment_id = "pay-unknown"

        _ = self.rpc_send_wait(
            receiver=selected_uas["droneport_id"],
            action=PREPARE_DISPATCH,
            payload={
                "mission_id": mission_details["mission_id"],
                "uas_id": selected_uas["uas_id"],
            },
            timeout_s=30.0,
            expected_sender=selected_uas["droneport_id"],
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )

        agro_result = self.rpc_send_wait(
            receiver="agro_drone",
            action=AGRO_MISSION_RECEIVED,
            payload={
                "mission_details": mission_details,
                "uas_id": selected_uas["uas_id"],
                "droneport_id": selected_uas["droneport_id"],
                "insurance_payment_id": insurance_payment_id,
                "scenario": order.get("scenario_type"),
            },
            timeout_s=60.0,
            expected_sender="agro_drone",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )

        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "order_execution_completed": agro_result,
            },
        )

    def _on_uas_purchase(self, msg: Dict[str, Any]) -> None:
        quantity = int(msg["payload"].get("quantity", 0))
        target_droneport_id = msg["payload"].get("target_droneport_id")
        trace_id = msg.get("trace_id")
        parent_span_id = msg.get("span_id")

        if quantity <= 0 or not target_droneport_id:
            self.send_response(
                request_msg=msg,
                payload={"status": "error", "error": "invalid_purchase_request"},
            )
            return

        purchase = self.rpc_send_wait(
            receiver="vendor_uas",
            action=REQUEST_UAS_PURCHASE,
            payload=msg["payload"],
            timeout_s=30.0,
            expected_sender="vendor_uas",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
        if purchase.get("status") != "ok":
            self.send_response(request_msg=msg, payload=purchase)
            return

        new_uas_items: List[Dict[str, Any]] = []
        for uas_id in purchase["uas_purchase_result"]["registered_uas_ids"]:
            new_uas_items.append(
                {
                    "uas_id": uas_id,
                    "model_id": msg["payload"].get("model_id", "new-model"),
                    "supported_task_types": msg["payload"].get("supported_task_types", ["agro"]),
                    "base_cost": float(msg["payload"].get("base_cost", 10000.0)),
                }
            )

        assigned = self.rpc_send_wait(
            receiver=target_droneport_id,
            action=ASSIGN_UAS_TO_DRONEPORT,
            payload={"uas_items": new_uas_items},
            timeout_s=20.0,
            expected_sender=target_droneport_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
        if assigned.get("status") != "ok":
            self.send_response(request_msg=msg, payload=assigned)
            return

        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "uas_purchase_result": purchase["uas_purchase_result"],
                "attachment": {
                    "droneport_id": target_droneport_id,
                    "assigned_count": assigned["assigned_count"],
                },
                "purchased_uas_items": new_uas_items,
            },
        )
