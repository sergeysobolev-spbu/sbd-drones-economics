"""
AgregatorComponent -- бизнес-логика агрегатора.

Обрабатывает заказы, взаимодействует с Operator, Insurer и ORVD через bus.

Интеграция с Fabric-леджером:
    Если задана переменная ENABLE_FABRIC_LEDGER=true, после подтверждения заказа
    (confirm_price) агрегатор публикует create_order в systems.dummy_fabric,
    а после завершения (confirm_completion) — finalize_order (fire-and-forget).
    Используется тот же order_id что и в основной системе, обеспечивая единый
    идентификатор между in-memory хранилищем и Fabric-леджером.
"""
import os
import uuid
from typing import Dict, Any, Optional

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus

from systems.agregator.src.agregator_component.topics import (
    ComponentTopics,
    ExternalTopics,
    AgregatorActions,
)

_FABRIC_ENABLED = os.environ.get("ENABLE_FABRIC_LEDGER", "false").lower() == "true"


class AgregatorComponent(BaseComponent):

    EXTERNAL_REQUEST_TIMEOUT = 15.0

    def __init__(self, component_id: str, bus: SystemBus):
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._operators: Dict[str, Dict[str, Any]] = {}
        self._customers: Dict[str, Dict[str, Any]] = {}
        self._commission_rate = 0.1

        super().__init__(
            component_id=component_id,
            component_type="agregator_component",
            topic=ComponentTopics.AGREGATOR_COMPONENT,
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler(AgregatorActions.CREATE_ORDER, self._handle_create_order)
        self.register_handler(AgregatorActions.LIST_ORDERS, self._handle_list_orders)
        self.register_handler(AgregatorActions.GET_ORDER, self._handle_get_order)
        self.register_handler(AgregatorActions.CONFIRM_PRICE, self._handle_confirm_price)
        self.register_handler(AgregatorActions.CONFIRM_COMPLETION, self._handle_confirm_completion)
        self.register_handler(AgregatorActions.REGISTER_OPERATOR, self._handle_register_operator)
        self.register_handler(AgregatorActions.REGISTER_CUSTOMER, self._handle_register_customer)

    def _handle_register_customer(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        name = payload.get("name", "")
        email = payload.get("email", "")
        if not name:
            raise ValueError("name is required")

        customer_id = str(uuid.uuid4())
        self._customers[customer_id] = {
            "id": customer_id,
            "name": name,
            "email": email,
        }
        return {"customer_id": customer_id}

    def _handle_register_operator(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        name = payload.get("name", "")
        license_number = payload.get("license", "")
        if not name:
            raise ValueError("name is required")

        cert_id = str(payload.get("certificate_id", "")).strip()
        operator_id = str(payload.get("operator_id", "")).strip() or str(uuid.uuid4())
        if cert_id:
            v = self.bus.request(
                ExternalTopics.REGULATOR,
                {
                    "action": "verify_operator_cert",
                    "sender": self.component_id,
                    "payload": {"operator_id": operator_id, "certificate_id": cert_id},
                },
                timeout=self.EXTERNAL_REQUEST_TIMEOUT,
            )
            if not v or not v.get("success") or not (v.get("payload") or {}).get("valid"):
                raise ValueError("regulator rejected operator certificate")
        self._operators[operator_id] = {
            "id": operator_id,
            "name": name,
            "license": license_number,
            "email": payload.get("email", ""),
            "certificate_id": cert_id or None,
        }
        return {"operator_id": operator_id}

    def _handle_create_order(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создаёт заказ и отправляет запрос на поиск дрона в Operator.
        """
        payload = message.get("payload", {})
        customer_id = payload.get("customer_id", "")
        description = payload.get("description", "")
        budget = payload.get("budget", 0)
        pickup = payload.get("pickup", {})
        dropoff = payload.get("dropoff", {})

        if not customer_id or customer_id not in self._customers:
            raise ValueError("valid customer_id is required")

        order_id = str(uuid.uuid4())
        order = {
            "id": order_id,
            "customer_id": customer_id,
            "description": description,
            "budget": budget,
            "pickup": pickup,
            "dropoff": dropoff,
            "status": "searching",
            "operator_id": None,
            "drone_id": None,
            "offered_price": None,
            "policy_id": None,
            "mission_id": None,
        }
        self._orders[order_id] = order

        response = self._request_operator_search(order)
        if response and response.get("success"):
            op_payload = response.get("payload", {})
            drones = op_payload.get("drones", [])
            if drones:
                best = drones[0]
                order["status"] = "matched"
                order["drone_id"] = best.get("drone_id")
                order["operator_id"] = best.get("operator_id", "")
                order["offered_price"] = best.get("price", budget)
            else:
                order["status"] = "no_drones"
        else:
            order["status"] = "search_failed"

        return {"order_id": order_id, "status": order["status"], "order": order}

    def _handle_list_orders(self, message: Dict[str, Any]) -> Dict[str, Any]:
        return {"orders": list(self._orders.values())}

    def _handle_get_order(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"order {order_id} not found")
        return {"order": order}

    def _handle_confirm_price(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подтверждает цену оператора, покупает страховку и регистрирует миссию.
        """
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"order {order_id} not found")
        if order["status"] != "matched":
            raise ValueError(f"order status is {order['status']}, expected 'matched'")

        insurance_resp = self._buy_insurance(order)
        if insurance_resp and insurance_resp.get("success"):
            ins_payload = insurance_resp.get("payload", {})
            order["policy_id"] = ins_payload.get("policy_id")
            order["insurance_premium"] = ins_payload.get("premium")
        else:
            order["status"] = "insurance_failed"
            error = "unknown"
            if insurance_resp:
                error = insurance_resp.get("error", error)
            return {"order_id": order_id, "status": order["status"], "error": f"insurance failed: {error}"}

        mission_resp = self._register_mission(order)
        if mission_resp and mission_resp.get("success"):
            ms_payload = mission_resp.get("payload", {})
            order["mission_id"] = ms_payload.get("mission_id", order_id)
        else:
            print(f"[{self.component_id}] ORVD mission registration failed (non-critical), proceeding")

        commission = (order.get("offered_price") or 0) * self._commission_rate
        order["commission"] = commission
        order["operator_amount"] = (order.get("offered_price") or 0) - commission
        order["status"] = "confirmed"

        # Фиксация заказа в Fabric-леджере. Используем тот же order_id, что и
        # в основной системе — это обеспечивает единый идентификатор в обоих хранилищах.
        insurance_premium = order.get("insurance_premium") or 0
        self._try_fabric("create_order", {
            "id": order_id,
            "aggregator_id": self.component_id,
            "operator_id": order.get("operator_id", ""),
            "drone_id": order.get("drone_id", ""),
            "insurer_id": ExternalTopics.INSURER,
            "cert_center_id": "",
            "developer_id": "",
            "fleet_price": order.get("offered_price", 0),
            "aggregator_fee": round(commission, 2),
            "insurance_premium": round(float(insurance_premium), 2),
            "risk_reserve": 0,
            "insurance_coverage_amount": order.get("budget", 0),
            "mission_insurance_id": order.get("policy_id", ""),
            "details": "[]",
        })

        return {"order_id": order_id, "status": "confirmed", "order": order}

    def _handle_confirm_completion(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")
        order = self._orders.get(order_id)
        if not order:
            raise ValueError(f"order {order_id} not found")
        if order["status"] != "confirmed":
            raise ValueError(f"order status is {order['status']}, expected 'confirmed'")

        order["status"] = "completed"

        # Финализация заказа в Fabric-леджере (fire-and-forget)
        self._try_fabric("finalize_order", {"order_id": order_id})

        return {"order_id": order_id, "status": "completed"}

    # -------------------------------------------------------------------------
    # Fabric dual-write (fire-and-forget)
    # -------------------------------------------------------------------------

    def _try_fabric(self, action: str, payload: Dict[str, Any]) -> None:
        """
        Публикует событие в systems.dummy_fabric (fire-and-forget).

        Не блокирует основную операцию: ошибки только логируются.
        Активируется через переменную окружения ENABLE_FABRIC_LEDGER=true.
        """
        if not _FABRIC_ENABLED:
            return
        try:
            self.bus.publish(
                ExternalTopics.FABRIC,
                {
                    "action": action,
                    "sender": self.component_id,
                    "payload": payload,
                },
            )
        except Exception as exc:
            print(f"[{self.component_id}] Fabric write skipped ({action}): {exc}")

    # --- Inter-system communication ---

    def _request_operator_search(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Запрашивает у Operator доступные дроны для заказа."""
        return self.bus.request(
            ExternalTopics.OPERATOR,
            {
                "action": "request_available_drones",
                "sender": self.component_id,
                "payload": {
                    "order_id": order["id"],
                    "description": order.get("description", ""),
                    "budget": order.get("budget", 0),
                    "pickup": order.get("pickup", {}),
                    "dropoff": order.get("dropoff", {}),
                },
            },
            timeout=self.EXTERNAL_REQUEST_TIMEOUT,
        )

    def _buy_insurance(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Оформляет миссионное страхование у Insurer перед каждым вылетом.

        Pmission = Vcargo × Rrisk_class × Kenv × Kincident_history

        cargo_value  — объявленная стоимость груза (бюджет заказа).
        drone_type   — тип дрона из поля order["drone_type"] (default: delivery).
        env_factor   — Kenv из поля order["env_factor"] (default: 1.0).
        """
        return self.bus.request(
            ExternalTopics.INSURER,
            {
                "action": "mission_insurance",
                "sender": self.component_id,
                "payload": {
                    "order_id": order["id"],
                    "operator_id": order.get("operator_id", ""),
                    "drone_id": order.get("drone_id", ""),
                    "cargo_value": order.get("budget", 0),
                    "drone_type": order.get("drone_type", "delivery"),
                    "env_factor": order.get("env_factor", 1.0),
                },
            },
            timeout=self.EXTERNAL_REQUEST_TIMEOUT,
        )

    def _register_mission(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Регистрирует миссию в OpBD/ORVD."""
        route = []
        if order.get("pickup"):
            route.append(order["pickup"])
        if order.get("dropoff"):
            route.append(order["dropoff"])

        return self.bus.request(
            ExternalTopics.ORVD,
            {
                "action": "register_mission",
                "sender": self.component_id,
                "payload": {
                    "mission_id": order["id"],
                    "drone_id": order.get("drone_id", ""),
                    "route": route,
                },
            },
            timeout=self.EXTERNAL_REQUEST_TIMEOUT,
        )
