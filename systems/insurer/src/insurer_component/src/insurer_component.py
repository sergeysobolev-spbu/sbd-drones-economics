"""
InsurerComponent -- бизнес-логика страховщика.

Расчёт стоимости полисов (КБМ), покупка, обработка инцидентов, завершение полисов.
Перенесено из Java-реализации на Python + SDK.
"""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus

from systems.insurer.src.insurer_component.topics import (
    ComponentTopics,
    InsurerActions,
)


class InsurerComponent(BaseComponent):

    BASE_COST = Decimal("1000.00")
    BASE_KBM = Decimal("1.00")
    POLICY_DURATION_DAYS = 30
    KBM_INCIDENT_MULTIPLIER = Decimal("1.10")

    def __init__(self, component_id: str, bus: SystemBus):
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._incidents: Dict[str, Dict[str, Any]] = {}
        self._kbm_history: list = []

        self._manufacturer_kbms: Dict[str, Decimal] = {}
        self._operator_kbms: Dict[str, Decimal] = {}

        super().__init__(
            component_id=component_id,
            component_type="insurer_component",
            topic=ComponentTopics.INSURER_COMPONENT,
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler(InsurerActions.CALCULATE_POLICY, self._handle_calculate)
        self.register_handler(InsurerActions.PURCHASE_POLICY, self._handle_purchase)
        self.register_handler(InsurerActions.REPORT_INCIDENT, self._handle_incident)
        self.register_handler(InsurerActions.TERMINATE_POLICY, self._handle_terminate)

    def _get_manufacturer_kbm(self, manufacturer_id: str) -> Decimal:
        return self._manufacturer_kbms.get(manufacturer_id, self.BASE_KBM)

    def _get_operator_kbm(self, operator_id: str) -> Decimal:
        return self._operator_kbms.get(operator_id, self.BASE_KBM)

    def _calculate_cost(self, manufacturer_id: str, operator_id: str) -> Decimal:
        """cost = base_cost * manufacturer_kbm * operator_kbm"""
        m_kbm = self._get_manufacturer_kbm(manufacturer_id)
        o_kbm = self._get_operator_kbm(operator_id)
        return (self.BASE_COST * m_kbm * o_kbm).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _handle_calculate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Расчёт стоимости полиса без покупки."""
        payload = message.get("payload", {})
        manufacturer_id = payload.get("manufacturer_id", "")
        operator_id = payload.get("operator_id", "")

        cost = self._calculate_cost(manufacturer_id, operator_id)
        m_kbm = self._get_manufacturer_kbm(manufacturer_id)
        o_kbm = self._get_operator_kbm(operator_id)

        return {
            "calculated_cost": str(cost),
            "manufacturer_kbm": str(m_kbm),
            "operator_kbm": str(o_kbm),
            "coverage_amount": str(payload.get("coverage_amount", 0)),
        }

    def _handle_purchase(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Покупка страхового полиса."""
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")
        operator_id = payload.get("operator_id", "")
        drone_id = payload.get("drone_id", "")
        manufacturer_id = payload.get("manufacturer_id", operator_id)
        coverage_amount = Decimal(str(payload.get("coverage_amount", 0)))

        if not order_id:
            raise ValueError("order_id is required")

        policy_id = str(uuid.uuid4())
        policy_number = f"POL-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)
        cost = self._calculate_cost(manufacturer_id, operator_id)

        policy = {
            "id": policy_id,
            "policy_number": policy_number,
            "order_id": order_id,
            "manufacturer_id": manufacturer_id,
            "operator_id": operator_id,
            "drone_id": drone_id,
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=self.POLICY_DURATION_DAYS)).isoformat(),
            "cost": str(cost),
            "coverage_amount": str(coverage_amount if coverage_amount else cost * 10),
            "status": "active",
        }
        self._policies[policy_id] = policy

        return {
            "policy_id": policy_id,
            "policy_number": policy_number,
            "order_id": order_id,
            "start_date": policy["start_date"],
            "end_date": policy["end_date"],
            "cost": str(cost),
            "status": "active",
        }

    def _handle_incident(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка инцидента: регистрация, пересчёт КБМ."""
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")
        manufacturer_id = payload.get("manufacturer_id", "")
        operator_id = payload.get("operator_id", "")
        damage_amount = Decimal(str(payload.get("damage_amount", 0)))
        incident_data = payload.get("incident", {})

        policy = self._find_policy_by_order(order_id)
        if not policy:
            raise ValueError(f"no active policy for order {order_id}")

        if not manufacturer_id:
            manufacturer_id = policy.get("manufacturer_id", "")
        if not operator_id:
            operator_id = policy.get("operator_id", "")

        incident_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        incident_record = {
            "id": incident_id,
            "order_id": order_id,
            "policy_id": policy["id"],
            "damage_amount": str(damage_amount),
            "incident_date": now.isoformat(),
            "status": "processed",
            "details": incident_data,
        }
        self._incidents[incident_id] = incident_record

        old_m_kbm = self._get_manufacturer_kbm(manufacturer_id)
        new_m_kbm = (old_m_kbm * self.KBM_INCIDENT_MULTIPLIER).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        self._manufacturer_kbms[manufacturer_id] = new_m_kbm

        old_o_kbm = self._get_operator_kbm(operator_id)
        new_o_kbm = (old_o_kbm * self.KBM_INCIDENT_MULTIPLIER).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        self._operator_kbms[operator_id] = new_o_kbm

        self._kbm_history.append({
            "entity_id": manufacturer_id,
            "entity_type": "manufacturer",
            "old_kbm": str(old_m_kbm),
            "new_kbm": str(new_m_kbm),
            "incident_id": incident_id,
            "date": now.isoformat(),
        })
        self._kbm_history.append({
            "entity_id": operator_id,
            "entity_type": "operator",
            "old_kbm": str(old_o_kbm),
            "new_kbm": str(new_o_kbm),
            "incident_id": incident_id,
            "date": now.isoformat(),
        })

        return {
            "incident_id": incident_id,
            "order_id": order_id,
            "payment_amount": str(damage_amount),
            "new_manufacturer_kbm": str(new_m_kbm),
            "new_operator_kbm": str(new_o_kbm),
            "status": "processed",
        }

    def _handle_terminate(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Завершение полиса по order_id."""
        payload = message.get("payload", {})
        order_id = payload.get("order_id", "")

        policy = self._find_policy_by_order(order_id)
        if not policy:
            raise ValueError(f"no active policy for order {order_id}")

        policy["status"] = "terminated"
        policy["end_date"] = datetime.now(timezone.utc).isoformat()

        return {
            "policy_id": policy["id"],
            "order_id": order_id,
            "status": "terminated",
        }

    def _find_policy_by_order(self, order_id: str) -> dict | None:
        for policy in self._policies.values():
            if policy["order_id"] == order_id and policy["status"] == "active":
                return policy
        return None
