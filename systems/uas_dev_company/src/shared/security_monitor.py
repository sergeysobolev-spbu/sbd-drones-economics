"""Security monitor component with policy-based proxying."""

from __future__ import annotations

import json
import os
from typing import Any

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent

from shared.topics import Actions, ComponentTopics


PolicyKey = tuple[str, str, str]


class SecurityMonitorComponent(BaseComponent):
    """Deny-all security monitor based on sender/topic/action policies."""

    def __init__(
        self,
        component_id: str,
        bus: SystemBus,
        topic: str = ComponentTopics.SECURITY_MONITOR,
        policy_admin_sender: str | None = None,
        security_policies: str | None = None,
    ):
        self._policy_admin_sender = (
            policy_admin_sender if policy_admin_sender is not None else os.environ.get("POLICY_ADMIN_SENDER", "")
        ).strip()
        if security_policies is not None:
            self._policies = self._parse_policies(security_policies.strip())
        else:
            env_raw = os.environ.get("SECURITY_POLICIES", "").strip()
            if env_raw:
                self._policies = self._parse_policies(env_raw)
            else:
                from shared.security_policies import canonical_allow_rule_tuples

                self._policies = set(canonical_allow_rule_tuples())
        super().__init__(
            component_id=component_id,
            component_type="security_monitor",
            topic=topic,
            bus=bus,
        )

    def _register_handlers(self) -> None:
        self.register_handler("proxy_request", self._handle_proxy_request)
        self.register_handler("proxy_publish", self._handle_proxy_publish)
        self.register_handler("set_policy", self._handle_set_policy)
        self.register_handler("remove_policy", self._handle_remove_policy)
        self.register_handler("clear_policies", self._handle_clear_policies)
        self.register_handler("list_policies", self._handle_list_policies)

    def _handle_get_status(self, message: dict[str, Any]) -> dict[str, Any]:
        status = super()._handle_get_status(message)
        status["policies_count"] = len(self._policies)
        status["policy_admin_sender"] = self._policy_admin_sender
        return status

    def _parse_policies(self, raw: str) -> set[PolicyKey]:
        if not raw:
            return set()
        raw = raw.strip()
        policies: set[PolicyKey] = set()
        try:
            value = json.loads(raw)
            for item in value if isinstance(value, list) else []:
                if isinstance(item, dict):
                    sender = str(item.get("sender", "")).strip()
                    topic = str(item.get("topic", "")).strip()
                    action = str(item.get("action", "")).strip()
                    if sender and topic and action:
                        policies.add((sender, topic, action))
            return policies
        except json.JSONDecodeError:
            pass
        for chunk in raw.split(";"):
            parts = [part.strip() for part in chunk.split(",")]
            if len(parts) == 3 and all(parts):
                policies.add((parts[0], parts[1], parts[2]))
        return policies

    def _is_allowed(self, sender: str, target_topic: str, target_action: str) -> bool:
        if (sender, target_topic, target_action) in self._policies:
            return True
        for policy_sender, policy_topic, policy_action in self._policies:
            if policy_sender != sender:
                continue
            topic_matches = policy_topic == "*" or policy_topic == target_topic
            action_matches = policy_action == "*" or policy_action == target_action
            if topic_matches and action_matches:
                return True
        return False

    def _can_manage_policies(self, sender: str) -> bool:
        return bool(self._policy_admin_sender and sender == self._policy_admin_sender)

    def _extract_target(self, payload: dict[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
        target = payload.get("target") or {}
        target_topic = str(target.get("topic", "")).strip()
        target_action = str(target.get("action", "")).strip()
        data = payload.get("data") or {}
        if not target_topic or not target_action:
            return None
        return target_topic, target_action, data if isinstance(data, dict) else {}

    def _handle_proxy_request(self, message: dict[str, Any]) -> dict[str, Any]:
        sender = str(message.get("sender", "")).strip()
        target = self._extract_target(message.get("payload", {}) or {})
        if target is None:
            return {"ok": False, "error": "no_target_in_payload"}
        target_topic, target_action, data = target
        if not self._is_allowed(sender, target_topic, target_action):
            return {
                "ok": False,
                "error": "policy_denied",
                "sender": sender,
                "target_topic": target_topic,
                "target_action": target_action,
            }
        if not self._is_allowed(self.topic, target_topic, Actions.IPC_INBOUND_REQUEST):
            return {
                "ok": False,
                "error": "monitor_inbound_denied",
                "target_topic": target_topic,
                "target_action": target_action,
            }
        response = self.bus.request(
            target_topic,
            {"action": target_action, "sender": self.topic, "payload": data},
            timeout=float(os.environ.get("SECURITY_MONITOR_PROXY_REQUEST_TIMEOUT_S", "10")),
        )
        if response is None:
            return {"ok": False, "error": "target_timeout", "target_topic": target_topic}
        return {"target_topic": target_topic, "target_action": target_action, "target_response": response}

    def _handle_proxy_publish(self, message: dict[str, Any]) -> dict[str, Any] | None:
        sender = str(message.get("sender", "")).strip()
        target = self._extract_target(message.get("payload", {}) or {})
        if target is None:
            return None
        target_topic, target_action, data = target
        if not self._is_allowed(sender, target_topic, target_action):
            return None
        return {
            "published": bool(
                self.bus.publish(
                    target_topic,
                    {"action": target_action, "sender": self.topic, "payload": data},
                )
            )
        }

    def _policy_from_payload(self, payload: dict[str, Any]) -> PolicyKey | None:
        sender = str(payload.get("sender", "")).strip()
        topic = str(payload.get("topic", "")).strip()
        action = str(payload.get("action", "")).strip()
        if not sender or not topic or not action:
            return None
        return sender, topic, action

    def _handle_set_policy(self, message: dict[str, Any]) -> dict[str, Any]:
        if not self._can_manage_policies(str(message.get("sender", "")).strip()):
            return {"updated": False, "error": "forbidden"}
        policy = self._policy_from_payload(message.get("payload", {}) or {})
        if policy is None:
            return {"updated": False, "error": "invalid_policy"}
        self._policies.add(policy)
        return {"updated": True, "policy": self._policy_to_dict(policy)}

    def _handle_remove_policy(self, message: dict[str, Any]) -> dict[str, Any]:
        if not self._can_manage_policies(str(message.get("sender", "")).strip()):
            return {"removed": False, "error": "forbidden"}
        policy = self._policy_from_payload(message.get("payload", {}) or {})
        if policy is None:
            return {"removed": False, "error": "invalid_policy"}
        existed = policy in self._policies
        self._policies.discard(policy)
        return {"removed": existed, "policy": self._policy_to_dict(policy)}

    def _handle_clear_policies(self, message: dict[str, Any]) -> dict[str, Any]:
        if not self._can_manage_policies(str(message.get("sender", "")).strip()):
            return {"cleared": False, "error": "forbidden"}
        removed = len(self._policies)
        self._policies.clear()
        return {"cleared": True, "removed_count": removed}

    def _handle_list_policies(self, message: dict[str, Any]) -> dict[str, Any]:
        return {"count": len(self._policies), "policies": [self._policy_to_dict(policy) for policy in self._policies]}

    @staticmethod
    def _policy_to_dict(policy: PolicyKey) -> dict[str, str]:
        sender, topic, action = policy
        return {"sender": sender, "topic": topic, "action": action}
