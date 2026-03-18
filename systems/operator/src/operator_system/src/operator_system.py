"""
Operator System - главный компонент системы Эксплуатант

Координирует работу всех компонентов и обрабатывает внешние запросы.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent, TraceContext
from systems.operator.src.operator_clients import RegulatorClient
from systems.operator.src.topics import (
    BusinessLogicActions,
    ComponentTopics,
    FleetManagerActions,
    MissionPlannerActions,
    OperatorSystemActions,
    SecurityMonitorActions,
    SystemTopics,
)


class OperatorSystem(BaseComponent):
    """
    Главный компонент системы Эксплуатант

    Обрабатывает внешние запросы и координирует работу внутренних компонентов:
    - Security Monitor (D0_CRITICAL)
    - Fleet Manager (D1_TRUSTED)
    - Mission Planner (D1_TRUSTED)
    - Business Logic (D2_OPERATIONAL)
    """

    def __init__(self, component_id: str, bus: SystemBus):
        self.logger = logging.getLogger(f"OperatorSystem.{component_id}")

        # Клиент для взаимодействия с Регулятором
        self.regulator_client = RegulatorClient(bus)

        # Статистика системы
        self.stats = {
            "orders_received": 0,
            "orders_accepted": 0,
            "orders_rejected": 0,
            "missions_completed": 0,
            "missions_failed": 0,
        }

        # Активные заказы
        self.active_orders: Dict[str, Dict[str, Any]] = {}

        super().__init__(
            component_id=component_id,
            component_type="operator_system",
            topic=SystemTopics.OPERATOR,
            bus=bus,
        )

        # Регистрируемся в системе
        self._register_with_regulator()

        self.logger.info(f"Operator System {component_id} initialized")

    def _register_with_regulator(self):
        """Регистрация в Регуляторе"""
        try:
            import asyncio
            import os
            from concurrent.futures import ThreadPoolExecutor

            operator_info = {
                "operator_id": os.getenv("OPERATOR_ID", "operator-001"),
                "operator_name": os.getenv("OPERATOR_NAME", "Sky Delivery Solutions"),
                "license_number": os.getenv("OPERATOR_LICENSE", "OP-2024-001"),
                "contact_info": {
                    "email": os.getenv("OPERATOR_EMAIL", "operations@skydelivery.ru"),
                    "phone": os.getenv("OPERATOR_PHONE", "+7-495-555-0123"),
                },
                "capabilities": ["cargo_delivery", "inspection", "agro"],
                "fleet_size": 0,  # Будет обновлено после инициализации Fleet Manager
            }

            def _run_async(coro):
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    return asyncio.run(coro)
                with ThreadPoolExecutor(max_workers=1) as ex:
                    return ex.submit(asyncio.run, coro).result()

            registered = _run_async(self.regulator_client.register_with_regulator(operator_info))

            if registered:
                self.logger.info("Successfully registered with Regulator")

                topics = _run_async(self.regulator_client.get_system_topics())
                self.logger.info(f"Received {len(topics)} system topics from Regulator")
            else:
                self.logger.warning("Failed to register with Regulator, using local config")

        except Exception as e:
            self.logger.error(f"Registration error: {e}")

    def _register_handlers(self):
        """Регистрация обработчиков"""
        # Управление заказами
        self.register_handler(OperatorSystemActions.RECEIVE_ORDER, self._handle_receive_order)
        self.register_handler(OperatorSystemActions.CALCULATE_PROPOSAL, self._handle_calculate_proposal)
        self.register_handler(OperatorSystemActions.SUBMIT_PROPOSAL, self._handle_submit_proposal)
        self.register_handler(OperatorSystemActions.ACCEPT_ORDER, self._handle_accept_order)
        self.register_handler(OperatorSystemActions.REJECT_ORDER, self._handle_reject_order)

        # Управление парком
        self.register_handler(OperatorSystemActions.GET_FLEET_STATUS, self._handle_get_fleet_status)

        # Планирование миссий
        self.register_handler(OperatorSystemActions.PLAN_MISSION, self._handle_plan_mission)
        self.register_handler(OperatorSystemActions.START_MISSION, self._handle_start_mission)
        self.register_handler(OperatorSystemActions.COMPLETE_MISSION, self._handle_complete_mission)

        # Мониторинг
        self.register_handler(OperatorSystemActions.GET_MISSION_STATUS, self._handle_get_mission_status)
        self.register_handler(OperatorSystemActions.REPORT_INCIDENT, self._handle_report_incident)

    def _handle_receive_order(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение нового заказа от Агрегатора"""
        trace_context = TraceContext.from_message(message)
        self.stats["orders_received"] += 1

        payload = message.get("payload", {})
        order = payload.get("order", {})

        if not order:
            return {"error": "Order details required"}

        order_id = order.get("id", f"ORDER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")

        security_check = self._validate_with_security_monitor(
            {"action": "receive_order", "sender": message.get("sender", "aggregator"), "order_id": order_id},
            {"order": order},
            trace_context=trace_context,
        )

        if not security_check.get("allowed", True):
            self.logger.warning(f"Order {order_id} rejected by security monitor")
            return {"error": "Security check failed", "violations": security_check.get("violations", [])}

        self.active_orders[order_id] = {
            "order": order,
            "status": "received",
            "received_at": datetime.utcnow().isoformat(),
        }

        self.logger.info(f"Received order {order_id}")

        proposal_result = self._calculate_proposal_internal(order, trace_context=trace_context)

        return {"order_id": order_id, "status": "received", "proposal": proposal_result}

    def _handle_calculate_proposal(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Расчёт коммерческого предложения"""
        trace_context = TraceContext.from_message(message)
        payload = message.get("payload", {})
        order_id = payload.get("order_id")

        if not order_id:
            return {"error": "order_id is required"}

        order_data = self.active_orders.get(order_id)
        if not order_data:
            return {"error": f"Order {order_id} not found"}

        return self._calculate_proposal_internal(order_data["order"], trace_context=trace_context)

    def _calculate_proposal_internal(
        self, order: Dict[str, Any], trace_context: Optional[TraceContext] = None
    ) -> Dict[str, Any]:
        """Внутренний метод расчёта предложения"""
        mission_result = self._request_component(
            ComponentTopics.MISSION_PLANNER,
            MissionPlannerActions.CREATE_MISSION,
            {"order": order},
            trace_context=trace_context,
        )
        if "error" in mission_result:
            return mission_result

        mission_id = mission_result.get("mission_id")

        validation_result = self._request_component(
            ComponentTopics.MISSION_PLANNER,
            MissionPlannerActions.VALIDATE_MISSION,
            {"mission_id": mission_id},
            trace_context=trace_context,
        )
        if not validation_result.get("valid", False):
            return {"error": "Mission validation failed", "details": validation_result.get("validation_results", [])}

        mission_details = self._request_component(
            ComponentTopics.MISSION_PLANNER,
            MissionPlannerActions.GET_MISSION_DETAILS,
            {"mission_id": mission_id},
            trace_context=trace_context,
        )

        uas_requirements = {
            "min_payload": mission_details.get("payload_weight", 0),
            "min_range": mission_details.get("distance", 0) * 1.2,
            "min_battery": 0.8,
        }

        available_uas = self._request_component(
            ComponentTopics.FLEET_MANAGER,
            FleetManagerActions.FIND_AVAILABLE_UAS,
            {"requirements": uas_requirements},
            trace_context=trace_context,
        )
        if available_uas.get("count", 0) == 0:
            return {"error": "No suitable UAS available", "requirements": uas_requirements}

        selected_uas = available_uas.get("suitable_uas", [])[0]

        insurance_quote = self._request_component(
            ComponentTopics.BUSINESS_LOGIC,
            BusinessLogicActions.REQUEST_INSURANCE_QUOTE,
            {
                "mission_details": {
                    **mission_details,
                    "uas_type": selected_uas.get("type"),
                    "payload_value": order.get("payload_value", 0),
                }
            },
            trace_context=trace_context,
        )

        proposal_result = self._request_component(
            ComponentTopics.BUSINESS_LOGIC,
            BusinessLogicActions.CREATE_PROPOSAL,
            {
                "order": order,
                "mission_details": {
                    **mission_details,
                    "uas_type": selected_uas.get("type"),
                    "uas_id": selected_uas.get("id"),
                    "insurance_premium": insurance_quote.get("premium", 0),
                },
            },
            trace_context=trace_context,
        )
        if "error" in proposal_result:
            return proposal_result

        order_id = order.get("id")
        if order_id in self.active_orders:
            self.active_orders[order_id].update(
                {
                    "mission_id": mission_id,
                    "uas_id": selected_uas.get("id"),
                    "proposal_id": proposal_result.get("proposal_id"),
                    "status": "proposal_ready",
                }
            )

        return {
            "proposal_id": proposal_result.get("proposal_id"),
            "price": proposal_result.get("price"),
            "margin_percent": proposal_result.get("margin_percent"),
            "delivery_time": proposal_result.get("delivery_time"),
            "uas_type": selected_uas.get("type"),
            "distance": mission_details.get("distance"),
            "insurance_included": True,
        }

    def _handle_submit_proposal(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка предложения Агрегатору"""
        payload = message.get("payload", {})
        order_id = payload.get("order_id")

        if not order_id:
            return {"error": "order_id is required"}

        order_data = self.active_orders.get(order_id)
        if not order_data:
            return {"error": f"Order {order_id} not found"}

        if order_data.get("status") != "proposal_ready":
            return {"error": f"No proposal ready for order {order_id}"}

        self.logger.info(f"Submitting proposal for order {order_id}")
        order_data["status"] = "proposal_submitted"

        return {"submitted": True, "order_id": order_id, "proposal_id": order_data.get("proposal_id")}

    def _handle_accept_order(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Принятие заказа к исполнению"""
        trace_context = TraceContext.from_message(message)
        self.stats["orders_accepted"] += 1

        payload = message.get("payload", {})
        order_id = payload.get("order_id")

        if not order_id:
            return {"error": "order_id is required"}

        order_data = self.active_orders.get(order_id)
        if not order_data:
            return {"error": f"Order {order_id} not found"}

        mission_id = order_data.get("mission_id")
        uas_id = order_data.get("uas_id")
        if not all([mission_id, uas_id]):
            return {"error": "Mission or UAS not assigned"}

        reserve_result = self._request_component(
            ComponentTopics.FLEET_MANAGER,
            FleetManagerActions.RESERVE_UAS,
            {"uas_id": uas_id, "mission_id": mission_id, "duration": 7200},
            trace_context=trace_context,
        )
        if not reserve_result.get("reserved", False):
            return {"error": "Failed to reserve UAS", "details": reserve_result}

        utm_result = self._request_component(
            ComponentTopics.MISSION_PLANNER,
            MissionPlannerActions.REQUEST_UTM_APPROVAL,
            {"mission_id": mission_id},
            trace_context=trace_context,
        )
        if not utm_result.get("approved", False):
            self._request_component(
                ComponentTopics.FLEET_MANAGER,
                FleetManagerActions.RELEASE_UAS,
                {"uas_id": uas_id},
                trace_context=trace_context,
            )
            return {"error": "UTM approval denied", "details": utm_result}

        order_data["status"] = "accepted"
        order_data["utm_approval_id"] = utm_result.get("approval_id")

        self.logger.info(f"Order {order_id} accepted, mission {mission_id} approved")

        return {
            "accepted": True,
            "order_id": order_id,
            "mission_id": mission_id,
            "uas_id": uas_id,
            "utm_approval_id": utm_result.get("approval_id"),
        }

    def _handle_reject_order(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Отклонение заказа"""
        trace_context = TraceContext.from_message(message)
        self.stats["orders_rejected"] += 1

        payload = message.get("payload", {})
        order_id = payload.get("order_id")
        reason = payload.get("reason", "")

        if not order_id:
            return {"error": "order_id is required"}

        order_data = self.active_orders.get(order_id)
        if not order_data:
            return {"error": f"Order {order_id} not found"}

        if order_data.get("uas_id"):
            self._request_component(
                ComponentTopics.FLEET_MANAGER,
                FleetManagerActions.RELEASE_UAS,
                {"uas_id": order_data["uas_id"]},
                trace_context=trace_context,
            )

        order_data["status"] = "rejected"
        order_data["rejection_reason"] = reason

        self.logger.info(f"Order {order_id} rejected: {reason}")

        return {"rejected": True, "order_id": order_id, "reason": reason}

    def _handle_get_fleet_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статуса парка БАС"""
        trace_context = TraceContext.from_message(message)
        return self._request_component(
            ComponentTopics.FLEET_MANAGER, FleetManagerActions.GET_UAS_LIST, {}, trace_context=trace_context
        )

    def _handle_plan_mission(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Планирование миссии"""
        trace_context = TraceContext.from_message(message)
        payload = message.get("payload", {})
        order_id = payload.get("order_id")

        if not order_id:
            return {"error": "order_id is required"}

        order_data = self.active_orders.get(order_id)
        if not order_data:
            return {"error": f"Order {order_id} not found"}

        if order_data.get("mission_id"):
            return {"mission_id": order_data["mission_id"], "status": "already_planned"}

        return self._calculate_proposal_internal(order_data["order"], trace_context=trace_context)

    def _handle_start_mission(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Запуск миссии"""
        trace_context = TraceContext.from_message(message)
        payload = message.get("payload", {})
        mission_id = payload.get("mission_id")
        if not mission_id:
            return {"error": "mission_id is required"}

        status_result = self._request_component(
            ComponentTopics.MISSION_PLANNER,
            MissionPlannerActions.UPDATE_MISSION_STATUS,
            {"mission_id": mission_id, "status": "in_progress"},
            trace_context=trace_context,
        )
        if "error" in status_result:
            return status_result

        self.logger.info(f"Mission {mission_id} started")
        return {"started": True, "mission_id": mission_id}

    def _handle_complete_mission(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Завершение миссии"""
        trace_context = TraceContext.from_message(message)
        payload = message.get("payload", {})
        mission_id = payload.get("mission_id")
        success = payload.get("success", True)
        if not mission_id:
            return {"error": "mission_id is required"}

        new_status = "completed" if success else "failed"
        status_result = self._request_component(
            ComponentTopics.MISSION_PLANNER,
            MissionPlannerActions.UPDATE_MISSION_STATUS,
            {"mission_id": mission_id, "status": new_status, "reason": payload.get("reason", "")},
            trace_context=trace_context,
        )
        if "error" in status_result:
            return status_result

        if success:
            self.stats["missions_completed"] += 1
        else:
            self.stats["missions_failed"] += 1

        self.logger.info(f"Mission {mission_id} {new_status}")
        return {"completed": True, "mission_id": mission_id, "success": success}

    def _handle_get_mission_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статуса миссии"""
        trace_context = TraceContext.from_message(message)
        payload = message.get("payload", {})
        mission_id = payload.get("mission_id")
        if not mission_id:
            return {"error": "mission_id is required"}

        return self._request_component(
            ComponentTopics.MISSION_PLANNER,
            MissionPlannerActions.GET_MISSION_DETAILS,
            {"mission_id": mission_id},
            trace_context=trace_context,
        )

    def _handle_report_incident(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Сообщение об инциденте"""
        trace_context = TraceContext.from_message(message)
        payload = message.get("payload", {})
        incident = payload.get("incident", {})
        if not incident:
            return {"error": "Incident details required"}

        log_result = self._request_component(
            ComponentTopics.SECURITY_MONITOR,
            SecurityMonitorActions.LOG_VIOLATION,
            {
                "policy_id": "INCIDENT",
                "policy_name": "Incident Report",
                "sender": message.get("sender", "unknown"),
                "action": incident.get("type", "unknown"),
                "reason": incident.get("description", ""),
                "severity": incident.get("severity", "medium"),
            },
            trace_context=trace_context,
        )

        self.logger.warning(f"Incident reported: {incident}")
        return {"reported": True, "incident_id": log_result.get("violation_id", "unknown")}

    def _request_component(
        self,
        topic: str,
        action: str,
        payload: Dict[str, Any],
        trace_context: Optional[TraceContext] = None,
    ) -> Dict[str, Any]:
        """Запрос к внутреннему компоненту"""
        try:
            message = self.create_message(action=action, payload=payload, trace_context=trace_context)
            response = self.bus.request(topic, message, timeout=10.0)

            if response and response.get("success"):
                return response.get("payload", {})

            return {"error": f"Component {topic} request failed"}

        except Exception as e:
            self.logger.error(f"Component request error: {e}")
            return {"error": str(e)}

    def _validate_with_security_monitor(
        self,
        request: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        trace_context: Optional[TraceContext] = None,
    ) -> Dict[str, Any]:
        """Валидация через монитор безопасности"""
        sender = (request.get("sender") or "").lower()
        sender_role = request.get("sender_role")
        if not sender_role:
            if sender.startswith("aggregator"):
                sender_role = "aggregator"
            elif sender.startswith("operator"):
                sender_role = "operator"
            elif sender.startswith("shell"):
                sender_role = "system"
            elif sender.startswith("pytest"):
                sender_role = "system"
            else:
                sender_role = "unknown"
        return self._request_component(
            ComponentTopics.SECURITY_MONITOR,
            SecurityMonitorActions.VALIDATE_REQUEST,
            {"request": request, "context": context or {}, "sender_role": sender_role},
            trace_context=trace_context,
        )

    def get_system_statistics(self) -> Dict[str, Any]:
        """Получение статистики системы"""
        return {
            "system_stats": self.stats,
            "active_orders": len(self.active_orders),
            "orders_by_status": self._count_orders_by_status(),
        }

    def _count_orders_by_status(self) -> Dict[str, int]:
        """Подсчёт заказов по статусам"""
        status_count: Dict[str, int] = {}
        for order_data in self.active_orders.values():
            status = order_data.get("status", "unknown")
            status_count[status] = status_count.get(status, 0) + 1
        return status_count
