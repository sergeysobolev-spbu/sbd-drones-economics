"""Таймауты GatewayBusBackend: короткое ожидание для authenticate/bootstrap."""

from __future__ import annotations

import asyncio

import pytest

from broker.system_bus import SystemBus
from gateway.bus_backend import GatewayBusBackend
from shared.topics import Actions, ComponentTopics


class StubBus(SystemBus):
    def __init__(self):
        self.last_timeout: float | None = None

    def publish(self, topic, message):
        return True

    def subscribe(self, topic, callback):
        return True

    def unsubscribe(self, topic):
        return True

    def request(self, topic, message, timeout=30.0):
        self.last_timeout = timeout
        return {
            "success": True,
            "payload": {
                "ok": True,
                "target_response": {"success": True, "payload": {"username": "u", "role": "администратор"}},
            },
        }

    def request_async(self, topic, message, timeout=30.0):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        fut = loop.create_future()
        fut.set_result(self.request(topic, message, timeout))
        return fut

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


def test_auth_uses_min_of_gateway_and_auth_timeout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GATEWAY_MONITOR_REQUEST_TIMEOUT_S", "120")
    monkeypatch.setenv("GATEWAY_AUTH_PROXY_TIMEOUT_S", "17")
    stub = StubBus()
    backend = GatewayBusBackend(bus=stub)
    out = backend.proxy(
        ComponentTopics.USER_MANAGEMENT,
        Actions.AUTHENTICATE,
        {"username": "a", "password": "b"},
    )
    assert out["username"] == "u"
    assert stub.last_timeout == 17.0


def test_other_user_management_uses_full_gateway_timeout(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GATEWAY_MONITOR_REQUEST_TIMEOUT_S", "99")
    monkeypatch.setenv("GATEWAY_AUTH_PROXY_TIMEOUT_S", "12")
    stub = StubBus()
    backend = GatewayBusBackend(bus=stub)
    backend.proxy(
        ComponentTopics.USER_MANAGEMENT,
        Actions.LIST_USERS,
        {"actor_role": "администратор"},
    )
    assert stub.last_timeout == 99.0
