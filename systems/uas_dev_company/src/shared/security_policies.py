"""Canonical security-monitor allow rules for api_gateway → backend traffic."""

from __future__ import annotations

import json

from shared.topics import Actions, ComponentTopics

# Воркеры, с которыми шлюз взаимодействует через proxy_request (и куда монитор ретранслирует RPC).
IPC_WORKER_TARGETS: tuple[str, ...] = (
    ComponentTopics.USER_MANAGEMENT,
    ComponentTopics.FIRMWARE_INGESTION,
    ComponentTopics.CERTIFICATION_SERVICE,
    ComponentTopics.DRONE_REGISTRY,
    ComponentTopics.PURCHASE_SERVICE,
    ComponentTopics.AUDIT_LOG,
)


def full_policy_dicts() -> list[dict[str, str]]:
    """Explicit allow-list entries (sender, topic, action) for the prototype."""
    g = ComponentTopics.API_GATEWAY
    mon = ComponentTopics.SECURITY_MONITOR
    rows: list[tuple[str, str, str]] = [
        (g, mon, Actions.PROXY_REQUEST),
        (g, ComponentTopics.USER_MANAGEMENT, Actions.BOOTSTRAP_ADMIN),
        (g, ComponentTopics.USER_MANAGEMENT, Actions.AUTHENTICATE),
        (g, ComponentTopics.USER_MANAGEMENT, Actions.CREATE_USER),
        (g, ComponentTopics.USER_MANAGEMENT, Actions.LIST_USERS),
        (g, ComponentTopics.USER_MANAGEMENT, Actions.ENABLE_USER),
        (g, ComponentTopics.USER_MANAGEMENT, Actions.DISABLE_USER),
        (g, ComponentTopics.USER_MANAGEMENT, Actions.DELETE_USER),
        (g, ComponentTopics.FIRMWARE_INGESTION, Actions.SUBMIT_FIRMWARE),
        (g, ComponentTopics.CERTIFICATION_SERVICE, Actions.CERTIFY_FIRMWARE),
        (g, ComponentTopics.CERTIFICATION_SERVICE, Actions.LIST_CERTIFICATES),
        (g, ComponentTopics.CERTIFICATION_SERVICE, Actions.REPORT_CRITICAL_VULNERABILITY),
        (g, ComponentTopics.DRONE_REGISTRY, Actions.REGISTER_DRONE),
        (g, ComponentTopics.DRONE_REGISTRY, Actions.LIST_REGISTERED_DRONES),
        (g, ComponentTopics.PURCHASE_SERVICE, Actions.PURCHASE_DRONE),
        (g, ComponentTopics.AUDIT_LOG, Actions.RECORD_AUDIT),
    ]
    rows.append((ComponentTopics.AUDIT_LOG, ComponentTopics.ANALYTICS_ADAPTER, Actions.SEND_ANALYTICS))
    for peer in (
        ComponentTopics.USER_MANAGEMENT,
        ComponentTopics.FIRMWARE_INGESTION,
        ComponentTopics.CERTIFICATION_SERVICE,
        ComponentTopics.DRONE_REGISTRY,
        ComponentTopics.PURCHASE_SERVICE,
    ):
        rows.append((peer, ComponentTopics.AUDIT_LOG, Actions.RECORD_AUDIT))
    # Задача 14: явные дуги IPC — одна политика на пару доменов для фазы «монитор → воркер»
    # и «воркер → монитор / монитор → шлюз» (ответы); учёт связей в метриках — по (отправитель, получатель), без умножения на ресурс.
    for wtopic in IPC_WORKER_TARGETS:
        rows.append((mon, wtopic, Actions.IPC_INBOUND_REQUEST))
        rows.append((wtopic, mon, Actions.IPC_RESPONSE))
    rows.append((mon, g, Actions.IPC_RESPONSE))
    return [{"sender": s, "topic": t, "action": a} for s, t, a in rows]


def canonical_allow_rule_tuples() -> set[tuple[str, str, str]]:
    return {(r["sender"], r["topic"], r["action"]) for r in full_policy_dicts()}


def full_policy_json() -> str:
    return json.dumps(full_policy_dicts(), ensure_ascii=False)
