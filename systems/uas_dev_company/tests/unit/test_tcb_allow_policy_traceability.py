"""Каждое allow-правило security-monitor трассируется к домену ДВБ (сценарий сертификации)."""

from __future__ import annotations

from shared.security_policies import IPC_WORKER_TARGETS, canonical_allow_rule_tuples
from shared.topics import Actions, ComponentTopics

G = ComponentTopics.API_GATEWAY
M = ComponentTopics.SECURITY_MONITOR


def _rule_tcb_domain_map() -> dict[tuple[str, str, str], str]:
    d: dict[tuple[str, str, str], str] = {
        (G, M, Actions.PROXY_REQUEST): "security_monitor_ipc",
        (G, ComponentTopics.USER_MANAGEMENT, Actions.BOOTSTRAP_ADMIN): "identity_auth",
        (G, ComponentTopics.USER_MANAGEMENT, Actions.AUTHENTICATE): "identity_auth",
        (G, ComponentTopics.USER_MANAGEMENT, Actions.CREATE_USER): "identity_auth",
        (G, ComponentTopics.USER_MANAGEMENT, Actions.LIST_USERS): "identity_auth",
        (G, ComponentTopics.USER_MANAGEMENT, Actions.ENABLE_USER): "identity_auth",
        (G, ComponentTopics.USER_MANAGEMENT, Actions.DISABLE_USER): "identity_auth",
        (G, ComponentTopics.USER_MANAGEMENT, Actions.DELETE_USER): "identity_auth",
        (G, ComponentTopics.FIRMWARE_INGESTION, Actions.SUBMIT_FIRMWARE): "artifact_certification_policy",
        (G, ComponentTopics.CERTIFICATION_SERVICE, Actions.CERTIFY_FIRMWARE): "artifact_certification_policy",
        (G, ComponentTopics.CERTIFICATION_SERVICE, Actions.LIST_CERTIFICATES): "artifact_certification_policy",
        (G, ComponentTopics.CERTIFICATION_SERVICE, Actions.REPORT_CRITICAL_VULNERABILITY): "artifact_certification_policy",
        (G, ComponentTopics.DRONE_REGISTRY, Actions.REGISTER_DRONE): "registry_purchase_policy",
        (G, ComponentTopics.DRONE_REGISTRY, Actions.LIST_REGISTERED_DRONES): "registry_purchase_policy",
        (G, ComponentTopics.PURCHASE_SERVICE, Actions.PURCHASE_DRONE): "registry_purchase_policy",
        (G, ComponentTopics.AUDIT_LOG, Actions.RECORD_AUDIT): "system_journal_boundary",
        (
            ComponentTopics.USER_MANAGEMENT,
            ComponentTopics.AUDIT_LOG,
            Actions.RECORD_AUDIT,
        ): "system_journal_boundary",
        (
            ComponentTopics.FIRMWARE_INGESTION,
            ComponentTopics.AUDIT_LOG,
            Actions.RECORD_AUDIT,
        ): "system_journal_boundary",
        (
            ComponentTopics.CERTIFICATION_SERVICE,
            ComponentTopics.AUDIT_LOG,
            Actions.RECORD_AUDIT,
        ): "system_journal_boundary",
        (
            ComponentTopics.DRONE_REGISTRY,
            ComponentTopics.AUDIT_LOG,
            Actions.RECORD_AUDIT,
        ): "system_journal_boundary",
        (
            ComponentTopics.PURCHASE_SERVICE,
            ComponentTopics.AUDIT_LOG,
            Actions.RECORD_AUDIT,
        ): "system_journal_boundary",
        (
            ComponentTopics.AUDIT_LOG,
            ComponentTopics.ANALYTICS_ADAPTER,
            Actions.SEND_ANALYTICS,
        ): "system_journal_boundary",
    }
    for wtopic in IPC_WORKER_TARGETS:
        d[(M, wtopic, Actions.IPC_INBOUND_REQUEST)] = "ipc_monitor_deliver"
        d[(wtopic, M, Actions.IPC_RESPONSE)] = "ipc_worker_reply"
    d[(M, G, Actions.IPC_RESPONSE)] = "ipc_monitor_to_gateway"
    return d


_RULE_TCB_DOMAIN = _rule_tcb_domain_map()


def test_each_allow_rule_has_tcb_domain() -> None:
    canon = canonical_allow_rule_tuples()
    assert _RULE_TCB_DOMAIN.keys() == canon, (
        "Обновите _rule_tcb_domain_map при изменении security_policies.full_policy_dicts()"
    )


def test_reported_tcb_domain_labels_stable() -> None:
    """Сводка для сертификации: фиксированный набор доменов ДВБ для allow-правил."""
    assert set(_RULE_TCB_DOMAIN.values()) == {
        "security_monitor_ipc",
        "identity_auth",
        "artifact_certification_policy",
        "registry_purchase_policy",
        "system_journal_boundary",
        "ipc_monitor_deliver",
        "ipc_worker_reply",
        "ipc_monitor_to_gateway",
    }
