"""
AgregatorGateway -- координатор системы агрегатора.

Проксирует bus-запросы к компоненту и предоставляет REST API для заказчика.
"""
from typing import Dict, Any, Optional

from flask import request, jsonify

from sdk.base_gateway import BaseGateway
from broker.system_bus import SystemBus

from systems.agregator.src.gateway.topics import (
    SystemTopics,
    ComponentTopics,
    GatewayActions,
)


class AgregatorGateway(BaseGateway):

    ACTION_ROUTING = {
        GatewayActions.CREATE_ORDER: ComponentTopics.AGREGATOR_COMPONENT,
        GatewayActions.LIST_ORDERS: ComponentTopics.AGREGATOR_COMPONENT,
        GatewayActions.GET_ORDER: ComponentTopics.AGREGATOR_COMPONENT,
        GatewayActions.CONFIRM_PRICE: ComponentTopics.AGREGATOR_COMPONENT,
        GatewayActions.CONFIRM_COMPLETION: ComponentTopics.AGREGATOR_COMPONENT,
        GatewayActions.REGISTER_OPERATOR: ComponentTopics.AGREGATOR_COMPONENT,
        GatewayActions.REGISTER_CUSTOMER: ComponentTopics.AGREGATOR_COMPONENT,
    }

    PROXY_TIMEOUT = 20.0

    def __init__(
        self,
        system_id: str,
        bus: SystemBus,
        health_port: Optional[int] = None,
    ):
        super().__init__(
            system_id=system_id,
            system_type="agregator",
            topic=SystemTopics.AGREGATOR,
            bus=bus,
            health_port=health_port,
        )

    def _setup_health_check(self):
        """Расширяем Flask-приложение REST-эндпоинтами для заказчика."""
        super()._setup_health_check()
        if not self._health_app:
            return

        app = self._health_app

        @app.route("/customers", methods=["POST"])
        def register_customer():
            data = request.get_json(silent=True) or {}
            return self._rest_proxy(GatewayActions.REGISTER_CUSTOMER, data)

        @app.route("/operators", methods=["POST"])
        def register_operator():
            data = request.get_json(silent=True) or {}
            return self._rest_proxy(GatewayActions.REGISTER_OPERATOR, data)

        @app.route("/orders", methods=["GET"])
        def list_orders():
            return self._rest_proxy(GatewayActions.LIST_ORDERS, {})

        @app.route("/orders", methods=["POST"])
        def create_order():
            data = request.get_json(silent=True) or {}
            return self._rest_proxy(GatewayActions.CREATE_ORDER, data)

        @app.route("/orders/<order_id>", methods=["GET"])
        def get_order(order_id):
            return self._rest_proxy(GatewayActions.GET_ORDER, {"order_id": order_id})

        @app.route("/orders/<order_id>/confirm-price", methods=["POST"])
        def confirm_price(order_id):
            return self._rest_proxy(GatewayActions.CONFIRM_PRICE, {"order_id": order_id})

        @app.route("/orders/<order_id>/confirm-completion", methods=["POST"])
        def confirm_completion(order_id):
            return self._rest_proxy(GatewayActions.CONFIRM_COMPLETION, {"order_id": order_id})

    def _rest_proxy(self, action: str, payload: dict):
        """Проксирует REST-запрос через bus к компоненту и возвращает JSON."""
        topic = self.ACTION_ROUTING.get(action)
        if not topic:
            return jsonify({"error": f"no route for action: {action}"}), 500

        response = self.bus.request(
            topic,
            {
                "action": action,
                "sender": self.system_id,
                "payload": payload,
            },
            timeout=self.PROXY_TIMEOUT,
        )

        if response is None:
            return jsonify({"error": "timeout"}), 504

        if response.get("success"):
            return jsonify(response.get("payload", {}))

        error = response.get("error", "unknown error")
        return jsonify({"error": error}), 400
