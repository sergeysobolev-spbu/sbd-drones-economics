#!/usr/bin/env python3
"""Топология IPC между доменами ДВБ: дедупликация связей (отправитель→получатель) по политикам (Задача 14)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SRC = ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from shared.topics import ComponentTopics  # noqa: E402

from tcb_container_domains import CONTAINER_TCB_PYTHON_DOMAINS  # noqa: E402

_TOPIC_TO_COMPOSE: dict[str, str] = {
    ComponentTopics.API_GATEWAY: "api_gateway",
    ComponentTopics.SECURITY_MONITOR: "security_monitor",
    ComponentTopics.USER_MANAGEMENT: "user_management_worker",
    ComponentTopics.FIRMWARE_INGESTION: "firmware_ingestion_worker",
    ComponentTopics.CERTIFICATION_SERVICE: "certification_service_worker",
    ComponentTopics.DRONE_REGISTRY: "drone_registry_worker",
    ComponentTopics.PURCHASE_SERVICE: "purchase_service_worker",
    ComponentTopics.AUDIT_LOG: "audit_log_worker",
    ComponentTopics.ANALYTICS_ADAPTER: "analytics_adapter_worker",
}


def policy_deduped_compose_edges(policy_rows: list[dict[str, str]]) -> set[tuple[str, str]]:
    """Одна связь на упорядоченную пару доменов compose, независимо от числа действий/ресурсов."""
    edges: set[tuple[str, str]] = set()
    for r in policy_rows:
        s = _TOPIC_TO_COMPOSE.get(str(r.get("sender", "")))
        t = _TOPIC_TO_COMPOSE.get(str(r.get("topic", "")))
        if s is None or t is None:
            continue
        edges.add((s, t))
    return edges


def compose_domain_security_goals() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for d in CONTAINER_TCB_PYTHON_DOMAINS:
        svc = str(d["compose_service"])
        goals = d.get("security_goals_ru")
        if isinstance(goals, list):
            out[svc] = [str(x) for x in goals]
        else:
            out[svc] = []
    return out


def build_ipc_topology_task14(policy_rows: list[dict[str, str]]) -> dict:
    edges = policy_deduped_compose_edges(policy_rows)
    edge_list = sorted(edges)
    goals_by_domain = compose_domain_security_goals()
    domains = [str(x["compose_service"]) for x in CONTAINER_TCB_PYTHON_DOMAINS]
    per_domain: list[dict] = []
    for svc in domains:
        inc = sorted({a for a, b in edges if b == svc})
        out_n = sorted({b for a, b in edges if a == svc})
        per_domain.append(
            {
                "compose_service": svc,
                "inbound_distinct_peers": len(inc),
                "outbound_distinct_peers": len(out_n),
                "inbound_peers_compose": inc,
                "outbound_peers_compose": out_n,
                "security_goals_ru": goals_by_domain.get(svc, []),
            }
        )
    return {
        "task": "Задача 14 — IPC-связи между доменами (дедуп по парам) и цели безопасности",
        "methodology_ru": (
            "Связь между доменами безопасности (сервисами compose) — это уникальная упорядоченная пара "
            "(отправитель, получатель), выведенная из allow-политик (sender, topic, …). Несколько правил с одной "
            "и той же парой доменов, отличающихся только действием или «ресурсом» запроса, дают одну связь. "
            "Фазы ответа по IPC отражены отдельными политиками ipc_response / ipc_inbound_request. "
            "Контроль доставки запроса от монитора к воркеру: проверка ipc_inbound_request в security_monitor."
        ),
        "deduped_directed_edge_count": len(edges),
        "deduped_directed_edges": [{"from": a, "to": b} for a, b in edge_list],
        "per_domain": per_domain,
    }
