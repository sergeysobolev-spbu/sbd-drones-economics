"""Round-trip assertions for Kafka-style monitor envelopes."""

from __future__ import annotations

import pytest

from gateway.bus_backend import BusInvocationError, unwrap_monitor_proxy_result


def test_unwrap_nested_success_payload():
    raw = {
        "success": True,
        "payload": {
            "ok": True,
            "target_topic": "t",
            "target_action": "a",
            "target_response": {"success": True, "payload": {"users": [{"username": "u"}]}},
        },
    }
    assert unwrap_monitor_proxy_result(raw) == {"users": [{"username": "u"}]}


def test_unwrap_policy_denied_raises():
    raw = {
        "success": True,
        "payload": {"ok": False, "error": "policy_denied"},
    }
    with pytest.raises(BusInvocationError, match="policy_denied"):
        unwrap_monitor_proxy_result(raw)


def test_none_raises_timeout_message():
    with pytest.raises(BusInvocationError, match="timeout"):
        unwrap_monitor_proxy_result(None)


def test_backend_error_bubbles():
    raw = {
        "success": True,
        "payload": {
            "ok": True,
            "target_response": {"success": False, "error": "boom"},
        },
    }
    with pytest.raises(BusInvocationError, match="boom"):
        unwrap_monitor_proxy_result(raw)
