"""Моки смежных систем на шине: валидация контракта и ответы для интеграционных тестов."""

from __future__ import annotations

import threading
from typing import Any

from broker.bus_factory import create_system_bus
from broker.src.system_bus import SystemBus

from shared.topics import ExternalTopics

from adjacent_contracts import (
    AdjacentContractError,
    validate_analytics_event,
    validate_drone_port_delivery_envelope,
    validate_operator_apply_decision,
    validate_operator_import_reregistered_envelope,
    validate_regulator_action_envelope,
)


class AdjacentBusMocks:
    """Подписка на системные топики смежных систем и синхронные ответы через bus.respond."""

    def __init__(
        self,
        *,
        broker_type: str,
        fake_regulator: Any,
        fake_operator: Any,
        fake_drone_port: Any | None = None,
        fake_analytics: Any | None = None,
        client_id: str = "adjacent_systems_bus_mocks",
    ):
        self._bus: SystemBus = create_system_bus(bus_type=broker_type, client_id=client_id)
        self._reg = fake_regulator
        self._op = fake_operator
        self._port = fake_drone_port
        self._analytics = fake_analytics
        self._lock = threading.Lock()
        self._started = False

    @property
    def bus(self) -> SystemBus:
        return self._bus

    def start(self) -> None:
        if self._started:
            return
        self._bus.start()
        self._bus.subscribe(ExternalTopics.regulator(), self._on_regulator)
        self._bus.subscribe(ExternalTopics.operator_fleet(), self._on_operator)
        if self._port is not None:
            self._bus.subscribe(ExternalTopics.drone_port(), self._on_drone_port)
        if self._analytics is not None:
            self._bus.subscribe(ExternalTopics.drone_analytics(), self._on_analytics)
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._bus.stop()
        self._started = False

    def _fail(self, message: dict[str, Any], err: Exception) -> None:
        self._bus.respond(
            message,
            {"ok": False, "error": str(err), "reason_code": "contract_violation"},
        )

    def _on_regulator(self, message: dict[str, Any]) -> None:
        if not message.get("reply_to"):
            return
        action = str(message.get("action") or "")
        payload = message.get("payload") or {}
        envelope = payload.get("envelope")
        if not isinstance(envelope, dict):
            self._bus.respond(
                message,
                {"ok": False, "error": "missing envelope", "reason_code": "invalid_request"},
            )
            return
        try:
            validate_regulator_action_envelope(action, envelope)
        except AdjacentContractError as e:
            self._fail(message, e)
            return
        try:
            with self._lock:
                if action == "certify_firmware":
                    out = self._reg.certify_firmware(envelope)
                elif action == "register_drone_instance":
                    out = self._reg.register_drone_instance(envelope)
                elif action == "reregister_drone_instance":
                    out = self._reg.reregister_drone_instance(envelope)
                elif action == "report_critical_vulnerability":
                    out = self._reg.report_critical_vulnerability(envelope)
                else:
                    self._bus.respond(
                        message,
                        {"ok": False, "error": "unknown action", "reason_code": "unknown_action"},
                    )
                    return
        except Exception as e:
            self._bus.respond(message, {"ok": False, "error": str(e), "reason_code": "handler_error"})
            return
        self._bus.respond(message, out)

    def _on_operator(self, message: dict[str, Any]) -> None:
        if not message.get("reply_to"):
            return
        action = str(message.get("action") or "")
        payload = message.get("payload") or {}
        envelope = payload.get("envelope")
        try:
            if not isinstance(envelope, dict):
                raise AdjacentContractError("missing envelope")
            if action == "import_drone_reregistered":
                validate_operator_import_reregistered_envelope(envelope)
                with self._lock:
                    self._op.import_drone_reregistered(envelope)
                self._bus.respond(message, {"ok": True})
            elif action == "apply_regulator_firmware_decision":
                validate_operator_apply_decision(envelope)
                with self._lock:
                    self._op.apply_regulator_firmware_decision(envelope)
                self._bus.respond(message, {"ok": True})
            else:
                self._bus.respond(message, {"ok": False, "error": "unknown action", "reason_code": "unknown_action"})
        except AdjacentContractError as e:
            self._fail(message, e)
        except Exception as e:
            self._bus.respond(message, {"ok": False, "error": str(e), "reason_code": "handler_error"})

    def _on_drone_port(self, message: dict[str, Any]) -> None:
        if not message.get("reply_to") or self._port is None:
            return
        payload = message.get("payload") or {}
        envelope = payload.get("envelope")
        if not isinstance(envelope, dict):
            self._bus.respond(message, {"ok": False, "error": "missing envelope"})
            return
        try:
            validate_drone_port_delivery_envelope(envelope)
            with self._lock:
                out = self._port.accept_delivered_drone(envelope)
        except AdjacentContractError as e:
            self._fail(message, e)
            return
        except Exception as e:
            self._bus.respond(message, {"ok": False, "error": str(e)})
            return
        self._bus.respond(message, out)

    def _on_analytics(self, message: dict[str, Any]) -> None:
        if not message.get("reply_to") or self._analytics is None:
            return
        payload = message.get("payload") or {}
        event = payload.get("event")
        try:
            validate_analytics_event(event)
            with self._lock:
                out = self._analytics.post_event(event) if isinstance(event, dict) else {"ok": False}
        except AdjacentContractError as e:
            self._fail(message, e)
            return
        except Exception as e:
            self._bus.respond(message, {"ok": False, "error": str(e)})
            return
        self._bus.respond(message, out)
