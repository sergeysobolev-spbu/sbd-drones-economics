"""Интеграционные проверки: каждая каноническая политика gateway→* даёт успешное proxy_request."""

from __future__ import annotations

import asyncio
import json

import pytest

from broker.system_bus import SystemBus
from shared.security_monitor import SecurityMonitorComponent
from shared.security_policies import full_policy_dicts, full_policy_json
from shared.topics import Actions, ComponentTopics


class StubBus(SystemBus):
    """Фиксирует целевой топик и отдаёт успешный «воркерный» конверт."""

    def __init__(self):
        self.targets: list[tuple[str, dict]] = []

    def publish(self, topic, message):
        return True

    def subscribe(self, topic, callback):
        return True

    def unsubscribe(self, topic):
        return True

    def request(self, topic, message, timeout=30.0):
        self.targets.append((topic, message))
        return {
            "success": True,
            "payload": {
                "ok": True,
                "username": "stub",
                "role": "администратор",
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


@pytest.fixture()
def gateway_monitor():
    bus = StubBus()
    mon = SecurityMonitorComponent(
        component_id="routes_test",
        bus=bus,
        policy_admin_sender=ComponentTopics.API_GATEWAY,
        security_policies=full_policy_json(),
        topic=ComponentTopics.SECURITY_MONITOR,
    )
    return mon, bus


def test_every_canonical_gateway_proxy_route_reaches_stub_worker(gateway_monitor):
    monitor, bus = gateway_monitor
    routes = json.loads(json.dumps(full_policy_dicts()))
    gateway_rows = [
        r
        for r in routes
        if r.get("sender") == ComponentTopics.API_GATEWAY and r["action"] != Actions.PROXY_REQUEST
    ]
    assert len(gateway_rows) >= 10
    for row in gateway_rows:
        topic = row["topic"]
        action = row["action"]
        result = monitor._handle_proxy_request(
            {
                "sender": ComponentTopics.API_GATEWAY,
                "payload": {
                    "target": {"topic": topic, "action": action},
                    "data": {"actor_role": "администратор"},
                },
            }
        )
        assert result.get("error") != "policy_denied"
        assert "target_response" in result
