"""Вызов смежных систем через SystemBus (контракт docs/topic_namespaces.md, интеграционные тесты)."""

from __future__ import annotations

from typing import Any

from broker.bus_factory import create_system_bus
from broker.src.system_bus import SystemBus

from shared.integration_adapters import DroneAnalyticsPort, DronePortPort, OperatorFleetPort, RegulatorPort
from shared.topics import ExternalTopics

UAS_SENDER = "systems.uas_dev_company"


def _unwrap_bus_dict(
    raw: dict[str, Any] | None,
    *,
    context: str,
    treat_ok_false_as_error: bool = True,
) -> dict[str, Any]:
    if raw is None:
        raise RuntimeError(f"{context}: timeout or empty response from bus")
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise RuntimeError(f"{context}: response payload is not a dict")
    if treat_ok_false_as_error and payload.get("ok") is False:
        raise ValueError(str(payload.get("error") or payload.get("reason_code") or "downstream rejected"))
    return payload


class BusRegulatorPort(RegulatorPort):
    """RPC к системному топику Регулятора."""

    def __init__(
        self,
        bus: SystemBus | None = None,
        *,
        client_id: str = "uas_bus_regulator_client",
        timeout: float = 90.0,
    ):
        self._owns = bus is None
        self._bus = bus or create_system_bus(client_id=client_id)
        self._timeout = timeout
        self._started = False

    def _ensure(self) -> None:
        if not self._started:
            self._bus.start()
            self._started = True

    def stop(self) -> None:
        if self._owns and self._started:
            self._bus.stop()
        self._started = False

    def _req(self, action: str, envelope: dict[str, Any]) -> dict[str, Any]:
        self._ensure()
        raw = self._bus.request(
            ExternalTopics.regulator(),
            {"action": action, "sender": UAS_SENDER, "payload": {"envelope": envelope}},
            timeout=self._timeout,
        )
        return _unwrap_bus_dict(raw, context=f"regulator.{action}")

    def certify_firmware(self, envelope: dict[str, Any]) -> dict[str, Any]:
        return self._req("certify_firmware", envelope)

    def register_drone_instance(self, envelope: dict[str, Any]) -> dict[str, Any]:
        return self._req("register_drone_instance", envelope)

    def reregister_drone_instance(self, envelope: dict[str, Any]) -> dict[str, Any]:
        return self._req("reregister_drone_instance", envelope)

    def report_critical_vulnerability(self, envelope: dict[str, Any]) -> dict[str, Any]:
        return self._req("report_critical_vulnerability", envelope)


class BusOperatorFleetPort(OperatorFleetPort):
    def __init__(
        self,
        bus: SystemBus | None = None,
        *,
        client_id: str = "uas_bus_operator_client",
        timeout: float = 90.0,
    ):
        self._owns = bus is None
        self._bus = bus or create_system_bus(client_id=client_id)
        self._timeout = timeout
        self._started = False

    def _ensure(self) -> None:
        if not self._started:
            self._bus.start()
            self._started = True

    def stop(self) -> None:
        if self._owns and self._started:
            self._bus.stop()
        self._started = False

    def import_drone_reregistered(self, envelope: dict[str, Any]) -> None:
        self._ensure()
        raw = self._bus.request(
            ExternalTopics.operator_fleet(),
            {
                "action": "import_drone_reregistered",
                "sender": UAS_SENDER,
                "payload": {"envelope": envelope},
            },
            timeout=self._timeout,
        )
        _ = _unwrap_bus_dict(raw, context="operator.import_drone_reregistered")

    def apply_regulator_firmware_decision(self, envelope: dict[str, Any]) -> None:
        self._ensure()
        raw = self._bus.request(
            ExternalTopics.operator_fleet(),
            {
                "action": "apply_regulator_firmware_decision",
                "sender": UAS_SENDER,
                "payload": {"envelope": envelope},
            },
            timeout=self._timeout,
        )
        _ = _unwrap_bus_dict(raw, context="operator.apply_regulator_firmware_decision")


class BusDronePortClient(DronePortPort):
    def __init__(
        self,
        bus: SystemBus | None = None,
        *,
        client_id: str = "uas_bus_drone_port_client",
        timeout: float = 90.0,
    ):
        self._owns = bus is None
        self._bus = bus or create_system_bus(client_id=client_id)
        self._timeout = timeout
        self._started = False

    def _ensure(self) -> None:
        if not self._started:
            self._bus.start()
            self._started = True

    def stop(self) -> None:
        if self._owns and self._started:
            self._bus.stop()
        self._started = False

    def accept_delivered_drone(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self._ensure()
        raw = self._bus.request(
            ExternalTopics.drone_port(),
            {
                "action": "accept_delivered_drone",
                "sender": UAS_SENDER,
                "payload": {"envelope": envelope},
            },
            timeout=self._timeout,
        )
        return _unwrap_bus_dict(raw, context="drone_port.accept_delivered_drone")


class BusDroneAnalyticsClient(DroneAnalyticsPort):
    def __init__(
        self,
        bus: SystemBus | None = None,
        *,
        client_id: str = "uas_bus_drone_analytics_client",
        timeout: float = 30.0,
    ):
        self._owns = bus is None
        self._bus = bus or create_system_bus(client_id=client_id)
        self._timeout = timeout
        self._started = False

    def _ensure(self) -> None:
        if not self._started:
            self._bus.start()
            self._started = True

    def stop(self) -> None:
        if self._owns and self._started:
            self._bus.stop()
        self._started = False

    def post_event(self, event: dict[str, Any]) -> dict[str, Any]:
        self._ensure()
        raw = self._bus.request(
            ExternalTopics.drone_analytics(),
            {
                "action": "post_event",
                "sender": UAS_SENDER,
                "payload": {"event": event},
            },
            timeout=self._timeout,
        )
        if raw is None:
            return {"ok": False, "error": "timeout", "status_code": 0}
        payload = raw.get("payload")
        if isinstance(payload, dict):
            return payload
        return {"ok": False, "error": "invalid response", "status_code": 0}
