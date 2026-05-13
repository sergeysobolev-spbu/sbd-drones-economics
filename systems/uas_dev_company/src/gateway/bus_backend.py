"""HTTP gateway → security_monitor → service workers (Kafka/MQTT bus)."""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any

from broker.bus_factory import create_system_bus
from broker.system_bus import SystemBus

from shared.models import SecurityEvent
from shared.monitor_proxy_unwrap import BusInvocationError, unwrap_monitor_proxy_result
from shared.tcb import AuthorizationError
from shared.topics import Actions, ComponentTopics, Roles

# Короткий таймаут для логина/bootstrap по шине — не ждать полный GATEWAY_MONITOR_REQUEST_TIMEOUT_S.
_AUTH_USER_MGMT_ACTIONS = frozenset({Actions.AUTHENTICATE, Actions.BOOTSTRAP_ADMIN})


class GatewayBusBackend:
    """Synchronous RPCs from the REST gateway via the security_monitor."""

    def __init__(self, bus: SystemBus | None = None):
        self._owns_bus = bus is None
        self._bus = bus or create_system_bus(client_id="uas_dev_company_api_gateway")
        self._timeout = float(os.environ.get("GATEWAY_MONITOR_REQUEST_TIMEOUT_S", "30"))
        # Не ниже типичного round-trip шины при холодном старте (e2e / CI); см. docker-compose.
        self._auth_timeout = float(os.environ.get("GATEWAY_AUTH_PROXY_TIMEOUT_S", "60"))

    @property
    def bus(self) -> SystemBus:
        return self._bus

    def start(self) -> None:
        self._bus.start()

    def stop(self) -> None:
        if self._owns_bus:
            self._bus.stop()

    def _request_timeout(self, target_topic: str, target_action: str) -> float:
        """Для аутентификации и первичного админа — ограничить ожидание ответа монитора/воркера."""
        if target_topic == ComponentTopics.USER_MANAGEMENT and target_action in _AUTH_USER_MGMT_ACTIONS:
            return min(self._timeout, self._auth_timeout)
        return self._timeout

    def proxy(self, target_topic: str, target_action: str, data: dict[str, Any]) -> dict[str, Any]:
        message = {
            "action": Actions.PROXY_REQUEST,
            "sender": ComponentTopics.API_GATEWAY,
            "payload": {
                "target": {"topic": target_topic, "action": target_action},
                "data": data,
            },
        }
        raw = self._bus.request(
            ComponentTopics.SECURITY_MONITOR,
            message,
            timeout=self._request_timeout(target_topic, target_action),
        )
        return unwrap_monitor_proxy_result(raw)


class BusApiContext:
    """Same surface as ApiContext for HTTP handlers; calls go through the monitor."""

    def __init__(self, backend: GatewayBusBackend | None = None):
        self._backend = backend or GatewayBusBackend()
        self.users = _BusUsers(self._backend)
        self.firmware = _BusFirmware(self._backend)
        self.certification = _BusCertification(self._backend)
        self.registry = _BusDroneRegistry(self._backend)
        self.purchase = _BusPurchase(self._backend)
        self.audit = _BusAudit(self._backend)

    @property
    def jwt_secret(self) -> str:
        return os.environ.get("JWT_SECRET", "uas_dev_company_dev_jwt_change_me_in_production").strip()

    @property
    def backend(self) -> GatewayBusBackend:
        return self._backend

    def start(self) -> None:
        self._backend.start()

    def stop(self) -> None:
        self._backend.stop()


class _BusUsers:
    def __init__(self, backend: GatewayBusBackend):
        self._b = backend

    def bootstrap_admin(self, username: str, password: str) -> dict[str, Any]:
        return self._b.proxy(
            ComponentTopics.USER_MANAGEMENT,
            Actions.BOOTSTRAP_ADMIN,
            {"username": username, "password": password},
        )

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
        return self._b.proxy(
            ComponentTopics.USER_MANAGEMENT,
            Actions.AUTHENTICATE,
            {"username": username, "password": password},
        )

    def create_user(self, actor_role: str, username: str, role: str, password: str) -> dict[str, Any]:
        return self._b.proxy(
            ComponentTopics.USER_MANAGEMENT,
            Actions.CREATE_USER,
            {"actor_role": actor_role, "username": username, "role": role, "password": password},
        )

    def list_users(self, actor_role: str) -> list[dict[str, Any]]:
        data = self._b.proxy(
            ComponentTopics.USER_MANAGEMENT,
            Actions.LIST_USERS,
            {"actor_role": actor_role},
        )
        return data.get("users", [])

    def set_user_active(self, actor_role: str, username: str, is_active: bool) -> dict[str, Any]:
        action = Actions.ENABLE_USER if is_active else Actions.DISABLE_USER
        return self._b.proxy(
            ComponentTopics.USER_MANAGEMENT,
            action,
            {"actor_role": actor_role, "username": username},
        )

    def delete_user(self, actor_role: str, username: str) -> dict[str, Any]:
        return self._b.proxy(
            ComponentTopics.USER_MANAGEMENT,
            Actions.DELETE_USER,
            {"actor_role": actor_role, "username": username},
        )


class _BusFirmware:
    def __init__(self, backend: GatewayBusBackend):
        self._b = backend

    def submit(self, actor_role: str, submitted_by: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._b.proxy(
            ComponentTopics.FIRMWARE_INGESTION,
            Actions.SUBMIT_FIRMWARE,
            {"actor_role": actor_role, "submitted_by": submitted_by, "data": payload},
        )


class _BusCertification:
    def __init__(self, backend: GatewayBusBackend):
        self._b = backend

    def certify(self, actor_role: str, requested_by: str, firmware_id: str) -> dict[str, Any]:
        return self._b.proxy(
            ComponentTopics.CERTIFICATION_SERVICE,
            Actions.CERTIFY_FIRMWARE,
            {"actor_role": actor_role, "requested_by": requested_by, "firmware_id": firmware_id},
        )

    def list_certificates(self, actor_role: str) -> list[dict[str, Any]]:
        data = self._b.proxy(
            ComponentTopics.CERTIFICATION_SERVICE,
            Actions.LIST_CERTIFICATES,
            {"actor_role": actor_role},
        )
        return data.get("certificates", [])


class _BusDroneRegistry:
    def __init__(self, backend: GatewayBusBackend):
        self._b = backend

    def register(self, actor_role: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._b.proxy(
            ComponentTopics.DRONE_REGISTRY,
            Actions.REGISTER_DRONE,
            {"actor_role": actor_role, "data": payload},
        )

    def list_registered(self, actor_role: str) -> list[dict[str, Any]]:
        if actor_role not in (Roles.DEVELOPER, Roles.OPERATOR):
            raise AuthorizationError("role разработчик or эксплуатант is required")
        data = self._b.proxy(
            ComponentTopics.DRONE_REGISTRY,
            Actions.LIST_REGISTERED_DRONES,
            {"actor_role": actor_role},
        )
        return data.get("drones", [])


class _BusPurchase:
    def __init__(self, backend: GatewayBusBackend):
        self._b = backend

    def purchase(self, actor_role: str, operator_username: str, serial_number: str) -> dict[str, Any]:
        return self._b.proxy(
            ComponentTopics.PURCHASE_SERVICE,
            Actions.PURCHASE_DRONE,
            {
                "actor_role": actor_role,
                "operator_username": operator_username,
                "serial_number": serial_number,
            },
        )


class _BusAudit:
    def __init__(self, backend: GatewayBusBackend):
        self._b = backend

    def log(self, event: SecurityEvent) -> dict[str, Any]:
        return self._b.proxy(
            ComponentTopics.AUDIT_LOG,
            Actions.RECORD_AUDIT,
            {"event": asdict(event)},
        )
