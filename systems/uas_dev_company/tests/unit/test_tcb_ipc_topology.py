"""Задача 14: дедупликация IPC-связей между доменами по политикам."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from shared.security_policies import full_policy_dicts  # noqa: E402
from tcb_ipc_topology import build_ipc_topology_task14, policy_deduped_compose_edges  # noqa: E402


def test_gateway_to_worker_edges_deduped_to_one_per_worker() -> None:
    rows = full_policy_dicts()
    edges = policy_deduped_compose_edges(rows)
    assert ("api_gateway", "user_management_worker") in edges
    # Несколько действий user_management — одна дуга api_gateway → user_management_worker
    gw_um = sum(1 for a, b in edges if a == "api_gateway" and b == "user_management_worker")
    assert gw_um == 1


def test_build_ipc_topology_has_symmetric_reply_edges() -> None:
    block = build_ipc_topology_task14(full_policy_dicts())
    edges = {(e["from"], e["to"]) for e in block["deduped_directed_edges"]}
    assert ("security_monitor", "user_management_worker") in edges
    assert ("user_management_worker", "security_monitor") in edges
    assert ("security_monitor", "api_gateway") in edges
    assert block["deduped_directed_edge_count"] == len(edges)


def test_security_goals_present_per_domain() -> None:
    block = build_ipc_topology_task14(full_policy_dicts())
    by_svc = {p["compose_service"]: p for p in block["per_domain"]}
    for svc, row in by_svc.items():
        assert row["security_goals_ru"], svc
