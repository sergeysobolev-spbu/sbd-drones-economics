"""Unit tests for the UAS development company security monitor."""

from __future__ import annotations

import asyncio
import json

from broker.system_bus import SystemBus
from shared.component_base import ServiceComponent
from shared.security_monitor import SecurityMonitorComponent
from shared.topics import Actions, ComponentTopics


class DummyBus(SystemBus):
    def __init__(self):
        self.published = []
        self.requests = []

    def publish(self, topic, message):
        self.published.append((topic, message))
        return True

    def subscribe(self, topic, callback):
        return True

    def unsubscribe(self, topic):
        return True

    def request(self, topic, message, timeout=30.0):
        self.requests.append((topic, message, timeout))
        return {"success": True, "payload": {"ok": True}}

    def request_async(self, topic, message, timeout=30.0):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        future = loop.create_future()
        future.set_result(self.request(topic, message, timeout))
        return future

    def start(self):
        return None

    def stop(self):
        return None


def make_monitor(policies=None):
    return SecurityMonitorComponent(
        component_id="security_monitor_test",
        bus=DummyBus(),
        policy_admin_sender=ComponentTopics.API_GATEWAY,
        security_policies=json.dumps(policies or []),
    )


def test_deny_all_without_policy():
    monitor = make_monitor([])
    result = monitor._handle_proxy_request(
        {
            "sender": ComponentTopics.API_GATEWAY,
            "payload": {
                "target": {"topic": ComponentTopics.USER_MANAGEMENT, "action": "create_user"},
                "data": {},
            },
        }
    )
    assert result["error"] == "policy_denied"
    assert monitor.bus.requests == []


def test_proxy_request_allowed_by_policy():
    monitor = make_monitor(
        [
            {
                "sender": ComponentTopics.API_GATEWAY,
                "topic": ComponentTopics.USER_MANAGEMENT,
                "action": "create_user",
            },
            {
                "sender": ComponentTopics.SECURITY_MONITOR,
                "topic": ComponentTopics.USER_MANAGEMENT,
                "action": Actions.IPC_INBOUND_REQUEST,
            },
        ]
    )
    result = monitor._handle_proxy_request(
        {
            "sender": ComponentTopics.API_GATEWAY,
            "payload": {
                "target": {"topic": ComponentTopics.USER_MANAGEMENT, "action": "create_user"},
                "data": {"username": "dev"},
            },
        }
    )
    assert result["target_response"]["success"] is True
    topic, message, _timeout = monitor.bus.requests[0]
    assert topic == ComponentTopics.USER_MANAGEMENT
    assert message["sender"] == ComponentTopics.SECURITY_MONITOR


def test_policy_admin_sender_required():
    monitor = make_monitor([])
    forbidden = monitor._handle_set_policy(
        {
            "sender": "other",
            "payload": {
                "sender": ComponentTopics.API_GATEWAY,
                "topic": ComponentTopics.USER_MANAGEMENT,
                "action": "create_user",
            },
        }
    )
    assert forbidden["updated"] is False

    allowed = monitor._handle_set_policy(
        {
            "sender": ComponentTopics.API_GATEWAY,
            "payload": {
                "sender": ComponentTopics.API_GATEWAY,
                "topic": ComponentTopics.USER_MANAGEMENT,
                "action": "create_user",
            },
        }
    )
    assert allowed["updated"] is True


def test_component_rejects_direct_backend_call():
    component = ServiceComponent(
        component_id="users",
        component_type="user_management",
        topic=ComponentTopics.USER_MANAGEMENT,
        bus=DummyBus(),
        handlers={"create_user": lambda payload: {"created": True}},
        trusted_sender=ComponentTopics.SECURITY_MONITOR,
    )

    direct = component._handlers["create_user"]({"sender": ComponentTopics.API_GATEWAY, "payload": {}})
    proxied = component._handlers["create_user"]({"sender": ComponentTopics.SECURITY_MONITOR, "payload": {}})

    assert direct["error"] == "direct_component_call_forbidden"
    assert proxied["created"] is True


def test_proxy_denied_without_monitor_inbound_policy():
    monitor = make_monitor(
        [
            {
                "sender": ComponentTopics.API_GATEWAY,
                "topic": ComponentTopics.USER_MANAGEMENT,
                "action": "create_user",
            },
        ]
    )
    result = monitor._handle_proxy_request(
        {
            "sender": ComponentTopics.API_GATEWAY,
            "payload": {
                "target": {"topic": ComponentTopics.USER_MANAGEMENT, "action": "create_user"},
                "data": {"username": "dev"},
            },
        }
    )
    assert result.get("error") == "monitor_inbound_denied"
    assert monitor.bus.requests == []
