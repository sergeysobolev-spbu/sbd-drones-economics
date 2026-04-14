"""
OperatorComponent -- бизнес-логика оператора.

Управляет реестром дронов, обрабатывает запросы на поиск дронов,
взаимодействует с Insurer и ORVD через bus.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent

from systems.operator.src.operator_component.topics import (
    ComponentTopics,
    ExternalTopics,
    OperatorActions,
)


class OperatorComponent(BaseComponent):

    EXTERNAL_REQUEST_TIMEOUT = 15.0

    def __init__(
        self,
        component_id: str,
        bus: SystemBus,
        topic: str = ComponentTopics.OPERATOR_COMPONENT,
    ):
        self._drones: Dict[str, Dict[str, Any]] = {}
        super().__init__(
            component_id=component_id,
            component_type="operator",
            topic=topic,
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler(OperatorActions.REGISTER_DRONE, self._handle_register_drone)
        self.register_handler(OperatorActions.REQUEST_AVAILABLE_DRONES, self._handle_request_available_drones)
        self.register_handler(OperatorActions.SELECT_DRONE_AND_SEND_TO_AGGREGATOR, self._handle_select_drone)
        self.register_handler(OperatorActions.BUY_INSURANCE_POLICY, self._handle_buy_insurance)
        self.register_handler(OperatorActions.REGISTER_DRONE_IN_ORVD, self._handle_register_in_orvd)
        self.register_handler(OperatorActions.SEND_ORDER_TO_NUS, self._handle_send_to_nus)

    def _handle_register_drone(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Регистрирует дрон в реестре оператора."""
        payload = message.get("payload", {}) or {}
        drone_id = payload.get("drone_id", "")
        if not drone_id:
            raise ValueError("drone_id is required")

        cert_id = payload.get("certificate_id", "").strip()
        if cert_id:
            v = self.bus.request(
                ExternalTopics.REGULATOR,
                {
                    "action": "verify_drone_cert",
                    "sender": self.component_id,
                    "payload": {"drone_id": drone_id, "certificate_id": cert_id},
                },
                timeout=self.EXTERNAL_REQUEST_TIMEOUT,
            )
            if not v or not v.get("success") or not (v.get("payload") or {}).get("valid"):
                raise ValueError("regulator rejected drone certificate")

        self._drones[drone_id] = {
            "drone_id": drone_id,
            "model": payload.get("model", ""),
            "capabilities": payload.get("capabilities", {}),
            "status": "available",
            "operator_id": self.component_id,
        }
        print(f"[{self.component_id}] Drone {drone_id} registered")
        return {"status": "registered", "drone_id": drone_id}

    def _handle_request_available_drones(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Возвращает список доступных дронов, подходящих под критерии заказа."""
        payload = message.get("payload", {}) or {}

        available = [
            d for d in self._drones.values()
            if d["status"] == "available"
        ]

        result_drones = []
        for drone in available:
            result_drones.append({
                "drone_id": drone["drone_id"],
                "model": drone.get("model", ""),
                "operator_id": drone.get("operator_id", self.component_id),
                "price": payload.get("budget", 1000),
            })

        return {"drones": result_drones}

    def _handle_select_drone(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Выбирает дрон и помечает его как занятый."""
        payload = message.get("payload", {}) or {}
        drone_id = payload.get("selected_drone_id", "")
        order_id = payload.get("order_id", "")

        drone = self._drones.get(drone_id)
        if not drone:
            raise ValueError(f"drone {drone_id} not found")
        if drone["status"] != "available":
            raise ValueError(f"drone {drone_id} is not available (status: {drone['status']})")

        drone["status"] = "assigned"
        drone["assigned_order"] = order_id

        return {
            "drone_id": drone_id,
            "order_id": order_id,
            "status": "assigned",
        }

    def _handle_buy_insurance(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Покупает страховой полис у Insurer через bus."""
        payload = message.get("payload", {}) or {}
        drone_id = payload.get("drone_id", "")
        coverage_amount = payload.get("coverage_amount", 0)
        insurance_action = payload.get("insurance_action", "mission_insurance")

        response = self.bus.request(
            ExternalTopics.INSURER,
            {
                "action": insurance_action,
                "sender": self.component_id,
                "payload": {
                    "order_id": payload.get("order_id", ""),
                    "operator_id": self.component_id,
                    "drone_id": drone_id,
                    "coverage_amount": coverage_amount,
                },
            },
            timeout=self.EXTERNAL_REQUEST_TIMEOUT,
        )

        if response is None:
            raise TimeoutError("insurer did not respond")

        if response.get("success"):
            return {
                "status": "insured",
                "policy": response.get("payload", {}),
            }

        raise RuntimeError(f"insurance failed: {response.get('error', 'unknown')}")

    def _handle_register_in_orvd(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Регистрирует дрон в ORVD через bus."""
        payload = message.get("payload", {}) or {}
        drone_id = payload.get("drone_id", "")

        if not drone_id:
            raise ValueError("drone_id is required")

        orvd_payload: Dict[str, Any] = {
            "drone_id": drone_id,
            "model": payload.get("model", ""),
            "operator_id": self.component_id,
        }
        if payload.get("certificate_id"):
            orvd_payload["certificate_id"] = str(payload.get("certificate_id", "")).strip()

        response = self.bus.request(
            ExternalTopics.ORVD,
            {
                "action": "register_drone",
                "sender": self.component_id,
                "payload": orvd_payload,
            },
            timeout=self.EXTERNAL_REQUEST_TIMEOUT,
        )

        if response is None:
            raise TimeoutError("ORVD did not respond")

        if response.get("success"):
            return {
                "status": "registered_in_orvd",
                "drone_id": drone_id,
                "orvd_response": response.get("payload", {}),
            }

        raise RuntimeError(f"ORVD registration failed: {response.get('error', 'unknown')}")

    def _handle_send_to_nus(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Отправляет заказ в НУС (заглушка -- НУС не реализован)."""
        payload = message.get("payload", {}) or {}
        return {
            "status": "sent_to_nus",
            "order_id": payload.get("order_id", ""),
            "note": "NUS integration pending",
        }
