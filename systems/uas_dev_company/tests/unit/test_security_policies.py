"""Monitor default policy set matches the JSON export and env-less loader."""

from __future__ import annotations

import asyncio
import json

import pytest

from broker.system_bus import SystemBus

from shared.security_monitor import SecurityMonitorComponent
from shared.security_policies import (
    canonical_allow_rule_tuples,
    full_policy_dicts,
    full_policy_json,
)
from shared.topics import ComponentTopics


class _TinyBus(SystemBus):
    """Minimal bus stub — only policy parsing is exercised."""

    def publish(self, topic, message):
        return True

    def subscribe(self, topic, callback):
        return True

    def unsubscribe(self, topic):
        return True

    def request(self, topic, message, timeout=30.0):
        return {}

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


def test_full_policy_rows_count_stable():
    assert len(full_policy_dicts()) == 35


def test_json_roundtrip_equals_canonical():
    parsed_set = SecurityMonitorComponent(
        component_id="policies",
        bus=_TinyBus(),
        policy_admin_sender=ComponentTopics.API_GATEWAY,
        security_policies=full_policy_json(),
        topic=ComponentTopics.SECURITY_MONITOR,
    )._policies
    assert parsed_set == canonical_allow_rule_tuples()


def test_monitor_uses_builtin_policies_when_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SECURITY_POLICIES", raising=False)
    monitor = SecurityMonitorComponent(
        component_id="builtins",
        bus=_TinyBus(),
        policy_admin_sender=ComponentTopics.API_GATEWAY,
        security_policies=None,
    )
    assert monitor._policies == canonical_allow_rule_tuples()


def test_builtin_json_list_syntax_matches_canonical_pairs():
    data = json.loads(full_policy_json())
    triples = {(row["sender"], row["topic"], row["action"]) for row in data}
    assert triples == canonical_allow_rule_tuples()
